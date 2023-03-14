import socket
import copy

USE_SECTION_3_3_IMPROVEMENTS = True
USE_MAD = True
DRAFT_03 = True

# BASIC QUANTITIES  ------------------------------------------------------------

T_INTERVAL        = 350
N                 = 50
OBS_INTERVAL      = 10                # after 10 SBD observations make a decision to feedback
OBS_MERGE_THRESHOLD = 0.5

# SBD PARAMETERS  ------------------------------------------------------------

PV = 0.2                              # p_v
# THRESHOLD determine when flows are congested or not
CONGESTION_THRESHOLD      = 0.0       # c_s
HYSTERESIS_THRESHOLD      = 0.3       # c_h
LOSS_THRESHOLD            = 0.1       # p_l (from which value it looks upon loss instead of owd)

# DELTA THRESHOLD deal with grouping: Larger values split less (more tolerance)
KEYFREQ_DELTA_THRESHOLD   = 0.1       # p_f
VARIANCE_DELTA_THRESHOLD  = 0.3       # p_pdv
SKEWNESS_DELTA_THRESHOLD  = 0.1       # p_s
LOSS_DELTA_THRESHOLD      = 0.1       # p_d (difference in subflows' loss to be in same group)

if USE_SECTION_3_3_IMPROVEMENTS:
  # draft-02:
  CONGESTION_THRESHOLD      = -0.01   # c_s
  VARIANCE_DELTA_THRESHOLD  = 0.2     # p_pdv

if USE_MAD:
  PV                       = 0.7      # p_v
  VARIANCE_DELTA_THRESHOLD = 0.1      # p_mad (NB: same name as p_pdv!)

if DRAFT_03:
  SKEWNESS_DELTA_THRESHOLD  = 0.15       # p_s
  #M = 30
  #F = 20

# FETCH FROM KERNEL ------------------------------------------------------------

TCP_MPTCPSUBFLOWCOUNT = 29          #/* Gets the current number of subflows, 0 if not a MPTCP socket */
TCP_MPTCPSUBFLOWOWD = 30            #/* Retrieves OWD samples for a subflow */

from ctypes import *
try:
  cdll.LoadLibrary('libc.so.6')
  libc = CDLL('libc.so.6')
except:
  pass

class tcp_mptcpsubflowowd(Structure):
  _fields_  = [
    ('req_pathindex', c_int32),
    ('req_snapindex', c_int32),
    ('index', c_int32),
    ('sum_usecs', c_int64),
    ('max_usecs', c_int64),
    ('mad_var_sum', c_int64), # new for MAD
    ('count', c_int32),
    ('skew_lcount', c_int32),
    ('skew_rcount', c_int32),
    ('loss_count', c_int32),
  #  ('local_port', c_int32), #for emulation
]

def get_subflow_owd_snapshot(sock, pathindex, snapidx):
  data = tcp_mptcpsubflowowd()
  pdata = pointer(data)
  len_data = c_uint32(sizeof(tcp_mptcpsubflowowd))
  plen_data = pointer(len_data)

  data.req_pathindex = pathindex
  data.req_snapindex = snapidx

  res = libc.getsockopt(sock.fileno(), socket.SOL_TCP, TCP_MPTCPSUBFLOWOWD, pdata, plen_data)
  if res != 0:
    raise Exception('Failed to retreive TCP_MPTCPSUBFLOWOWD for pi={0}, idx={1} and space={2}'.format(pathindex, snapidx, len_data))

  return data

def _extend_path_owds(path_owds, owds):
  # if it is already there, just ignore it
  if path_owds and path_owds[-1]['index'] >= owds.index:
    return False

  snap = { 'index': owds.index,
           'sum_msecs': owds.sum_usecs / 1000.0,
           'max_msecs': owds.max_usecs / 1000.0,
           'mad_var_sum': owds.mad_var_sum / (1000.0 * 8) if owds.index > 0 else 0.0, # values are shifted left by 3, correct for that (*8), don't have this value for first snapshot
           'mean_msecs': owds.sum_usecs / (1000.0 * owds.count) if owds.count > 0 else 0.0,
           'count': owds.count,
           'skew_lcount': owds.skew_lcount if owds.index > 0 else 0, # we don't have an average mean in the first chunk, skewness is meaningless
           'skew_rcount': owds.skew_rcount if owds.index > 0 else 0,
           'loss_count': owds.loss_count,
           'local_port': 0 } #owds.local_port } #for emulation
  path_owds.append(snap)
  return True

def _cutoff_path_owds(path_owds, count):
  while len(path_owds) > count:
    del path_owds[0]

def update_owds(paths_owds, sock):
  subflows = sock.getsockopt(socket.IPPROTO_TCP, TCP_MPTCPSUBFLOWCOUNT) # TODO: actually want the highest pi!
  if paths_owds:
    highest_idx = max(paths_owds.keys())
    subflows = max(subflows, highest_idx)
  for i in range(subflows):
    pi = i + 1

    try:
      # fetch the last, could also go back and fetch missing ones!
      last_owds = get_subflow_owd_snapshot(sock, pi, -1)
    except:
      if pi in paths_owds:
        paths_owds[pi] = [] # empty list
      continue

    if not pi in paths_owds:
      paths_owds[pi] = [] # empty list
    _extend_path_owds(paths_owds[pi], last_owds)
    _cutoff_path_owds(paths_owds[pi], N)

# SBD CALCULATIONS -------------------------------------------------------------

def _avg(values):
  return sum(values) / float(len(values))

def _avg_masked(values, mask):
  count = 0
  summed = 0
  for i in range(len(values)):
    if mask[i]:
      summed += values[i]
      count += 1
  return summed / float(count)

def _pdv(chunk):
  return chunk['max_msecs'] - chunk['mean_msecs'] # ToDo: min instead of max:
                                                  # chunk['mean_msecs'] - min(chunk)

def _compute_bottleneck_freq(chunks, mean, variance, mask = None):
  interval = (mean - PV * variance, mean + PV * variance)   #p_v * E_N(PDV) from E_N(E_T(OWD))

  crossings = 0
  last_region = 2
  for idx in range(len(chunks)):
    v = chunks[idx]['mean_msecs']                           #E_T(owd)
    if v > interval[1]:
      region = 1
    elif v < interval[0]:
      region = -1
    else:
      region = 0

    if last_region == 2:
      last_region = region
      continue

    if last_region != region and (region == -1 or region == 1):
    # OLD BUGGY: if (last_region == 1 and region == -1) or (last_region == -1 and region == 1):
      if not mask or mask[idx]: # if we have congestion info: only record a significant mean crossing if flow is experiencing congestion
        crossings += 1
      last_region = region

  return crossings / float(len(chunks))         #freq_est = number_of_crossings / N

def _compute_skewness(chunk):
  left  = chunk['skew_lcount'] # OWD < E_M(E_T(OWD))
  right = chunk['skew_rcount'] # OWD > E_M(E_T(OWD))
  return float(left - right) / chunk['count']

def _compute_skewness_base(chunk):
  left  = chunk['skew_lcount'] # OWD < E_M(E_T(OWD))
  right = chunk['skew_rcount'] # OWD > E_M(E_T(OWD))
  return left - right

def _compute_filtered_skewness(chunks):
  skewbase_T  = [_compute_skewness_base(x) for x in chunks]
  nrsamples_T = [x['count'] for x in chunks]
  return sum(skewbase_T) / float(sum(nrsamples_T))

def _compute_mad(chunks): 
  madbase_T   = [x['mad_var_sum'] for x in chunks]
  nrsamples_T = [x['count'] for x in chunks]
  return sum(madbase_T) / float(sum(nrsamples_T))

def _compute_mean(chunks):
  means = []
  for chunk in chunks:
    means.append(chunk['mean_msecs']) #E_T(owd)
  return _avg(means)                  #E_N(E_T(owd))

def _process_path_owds(pi, owds):
  N_chunks = [x for x in owds if x['count'] > 0] # remove the empty ones
  if not N_chunks:
    return {}

  mean = _compute_mean(N_chunks)

  # 3.3. Removing Noise from the Estimates
  if USE_SECTION_3_3_IMPROVEMENTS:
    # 3.3.1.  Oscillation noise
    if USE_MAD:
      variance = _compute_mad(N_chunks)
      keyfreq  = _compute_bottleneck_freq(N_chunks, mean, variance) #David said to turn off masking, 03.10, mask = congestion_bits)
    else:
      # 3.3.2.  Removing noise
      congestion_bits = [(_compute_skewness(x) < CONGESTION_THRESHOLD) for x in N_chunks]
      variance = _avg_masked([_pdv(x) for x in N_chunks], congestion_bits) if any(congestion_bits) else 0.0
      keyfreq  = _compute_bottleneck_freq(N_chunks, mean, variance, mask = congestion_bits)
    # 3.3.3.  Bias in the skewness measure
    skewness = _compute_filtered_skewness(N_chunks)
  else:
    if USE_MAD:
      variance = _compute_mad(N_chunks)
    else:
      variance = _avg([_pdv(x) for x in N_chunks])
    keyfreq  = _compute_bottleneck_freq(N_chunks, mean, variance)
    skewness = _avg([_compute_skewness(x) for x in N_chunks])

  total = sum([x['count'] for x in N_chunks])
  return {'pi': pi, 'mean': mean, 'skewness': skewness, 'var': variance, 'keyf': keyfreq, 'count': total}

def _process_path_losses(pi, owds): #PL_NT = sum_NT(loss pkt) / sum_NT(total pkt)
  losses = 0
  total  = 0
  for chunk in owds:
    losses += chunk['loss_count']
    total  += chunk['count'] # TODO + chunk['loss_count']
  return losses / float(total) if total > 0 else 0.0

def calculate_metrics_for_subflows(paths_owds):
  subflows = []
  idle_subflows = []
  for pi, owds in paths_owds.iteritems():
    subflow = _process_path_owds(pi, owds)
    if subflow:
      subflow['losses'] = _process_path_losses(pi, owds)
      if len(owds) > 0 and 'local_port' in owds[0]:
        subflow['local_port'] = owds[0]['local_port'] # just grab the first, they are all equal anyway
      else:
        subflow['local_port'] = 0
      subflows.append(subflow)
    else:
      subflow = {'pi': pi, 'mean': 0.0, 'skewness': 0.0, 'var': 0.0, 'keyf': 0.0, 'count': 0, 'losses': 0.0, 'local_port': 0}
      idle_subflows.append(subflow)
  return subflows, idle_subflows

# SBD GROUPING ALGORITHM -------------------------------------------------------

def _split_congestion(flows, last_time_cong_flows):
  not_congested = []
  congested = []
  for flow in flows:
    PC = True if flow['pi'] in last_time_cong_flows else False
    if (flow['skewness'] < CONGESTION_THRESHOLD) or (flow['skewness'] < HYSTERESIS_THRESHOLD and PC) or (flow['losses'] > LOSS_THRESHOLD):
      congested.append(flow)
    else:
      not_congested.append(flow)
  return (not_congested, congested)

def _split_key_delta(flows, key, delta_thresh, flag): # flag: 'a' (absolute) or 'p' (proportional)
  # sort congested flows by key in descending order
  flows = sorted(flows, key=lambda flow: -flow[key]) # negate for descending order

  groups = []

  # if there are no flows, return immediately without groups
  if not flows:
    return groups

  # create the first group containing the first flow
  groups.append([flows[0]])

  # handle the rest: either insert into last existing group or create new group
  for flow in flows[1:]:
    last_group_tail = groups[-1][-1]                    #1. relative to closest in the CURRENT GROUP!

    belongs_to_last_group = False
    #absolute: 'a'
    if 'a' in flag:
      if last_group_tail[key] - flow[key] < delta_thresh:
        belongs_to_last_group = True
    #proportional: 'p'
    elif 'p' in flag:
      #cur_thresh = flows[0][key] * delta_thresh        # 1. relative to first of ALL FLOWS we are dealing with
      cur_thresh = last_group_tail[key] * delta_thresh  # 2. relative to first in the CURRENT GROUP (LCN'14)
      if last_group_tail[key] - flow[key] < cur_thresh:
        belongs_to_last_group = True
    if belongs_to_last_group:
      groups[-1].append(flow)
    else:
      groups.append([flow])

  return groups

def _split_skewness(flows):
    has_high_loss = False
    for flow in flows:
        if flow['losses'] > LOSS_THRESHOLD:
            has_high_loss = True
            break
    if has_high_loss:
        return _split_key_delta(flows, 'losses', LOSS_DELTA_THRESHOLD, 'a') #ToDo: 'p' ?
    else:
        return _split_key_delta(flows, 'skewness', SKEWNESS_DELTA_THRESHOLD, 'a')

def _print_groups(groups, logfile):
  count = 1
  for group in groups:
    for flow in group:
      sample_cnt = flow['count'] if 'count' in flow else 0
      local_port = flow['local_port'] if 'local_port' in flow else 0
      print >> logfile, '{0}. pi={1: 2d} mean={2:4.3f} var={3:5.3f} skew={4:.3f} keyf={5:.3f} loss={6:.5f}/{7:.2f}% samples={8} local_port={9}'.format(count, flow['pi'], flow['mean'], flow['var'], flow['skewness'], flow['keyf'], flow['losses'], flow['losses']*100, sample_cnt, local_port)
    count += 1

def get_congested_pis(groups):
  congested_pis = []
  for group in groups:
    for flow in group:
      congested_pis.append(flow['pi'])
  return congested_pis

def process_owds(paths_owds, congested_pis, logfile = None):
  subflows, idle_subflows = calculate_metrics_for_subflows(paths_owds)
  if not subflows:
    return idle_subflows, []

  #Congestion threshold: c_s, c_h, p_l
  #Here: if highly congested, use packet loss in some cases: but not if CCC -> CC
  (not_congested, congested) = _split_congestion(subflows, congested_pis)
  not_congested.extend(idle_subflows)
  if logfile:
    print >> logfile, len(not_congested), 'not congested:'
    _print_groups([not_congested], logfile)
    print >> logfile, '' # empty line
    print >> logfile, len(congested), 'congested:'
    _print_groups([congested], logfile)

  #Bottleneck frequency: p_f
  split_keyfreq = _split_key_delta(congested, 'keyf', KEYFREQ_DELTA_THRESHOLD, 'a')
  if logfile:
    print >> logfile, len(split_keyfreq), 'groups by key freq:'
    _print_groups(split_keyfreq, logfile)

  #PDV: p_pdv
  split_variance = []
  for group in split_keyfreq:
    local_split_variance = _split_key_delta(group, 'var', VARIANCE_DELTA_THRESHOLD, 'p')
    split_variance.extend(local_split_variance)
  if logfile:
    print >> logfile, len(split_variance), 'groups by variance:'
    _print_groups(split_variance, logfile)

  #Skewness: p_s
  split_skewness = []
  for group in split_variance:
    local_split_skewness = _split_skewness(group)
    split_skewness.extend(local_split_skewness)
  if logfile:
    print >> logfile, len(split_skewness), 'groups by skewness:'
    _print_groups(split_skewness, logfile)
    print >> logfile, '' # empty line
    print >> logfile, '' # empty line

  return not_congested, split_skewness

# FEEDBACK MERGING ...  --------------------------------------------------------

def build_observation(not_congested, groups):
  observation = []
  observation.extend(groups)
  for flow in not_congested:
    f = copy.copy(flow)
    f['nc'] = True # marker: non congested
    observation.append([f])
  return observation

def _is_noncongested_in_observation(ob, pi):
  for group in ob:
    for flow in group:
      if flow['pi'] == pi:
        non_congested = 'nc' in flow
        return non_congested
  return False # not found

def _is_noncongested_in_all_observations(observations, pi):
  for ob in observations:
    if not _is_noncongested_in_observation(ob, pi):
      return False
  return True

def _extract_pis(obs):
    obs2 = []
    for ob in obs:
        ob2 = []
        for group in ob:
            group2 = []
            for flow in group:
                group2.append(flow['pi'])
            ob2.append(group2)
        obs2.append(ob2)
    return obs2

def _get_all_subflows(observation_groups):
    pis = set()
    for ob in observation_groups:
        for group in ob:
            for flow in group:
              pis.add(flow)
    return sorted(list(pis))

def _find_all_groups(pi, observation_groups):
    pi_in_groups = []
    for ob in observation_groups:
        for group in ob:
            if pi in group:
                pi_in_groups.append(group)
    return pi_in_groups

def _visit(pi, visited, edges, final_group, threshold):
    # visit node only once
    if pi in visited:
        return
    # visit the node
    final_group.append(pi)
    visited.add(pi)
    # continue in graph
    for other, weight in edges[pi].items():
        if weight >= threshold: # visit only if edge is strong enough
            _visit(other, visited, edges, final_group, threshold)

#edge search, weighting
#at least X (threshold) decisions should be the same, otherwise split.
def merge_observations(observations, threshold):
    if len(observations) == 1: # no merging if there is only a single observation
        nc_group = []
        groups = []
        for group in observations[0]:
            if len(group) == 1 and 'nc' in group[0] and group[0]['nc']:
                nc_group.append(group[0]['pi'])
            else:
                pis = [f['pi'] for f in group]
                groups.append(pis)
        return nc_group, groups

    obs = _extract_pis(observations)
    pis = _get_all_subflows(obs)
    edges = {}
    for pi in pis:
        #encontra todos os grupos que consta pi
        groups = _find_all_groups(pi, obs)
        #pega todos os subfluxos que está junto com pi nos grupos pre selecionados anteriormente
        together = _get_all_subflows([groups])
        together.remove(pi)
        # calculate the weights for all other pis
        weighted = {}
        for other in together:
            count = 0
            for group in groups:
                if other in group:
                    count += 1
            weighted[other] = count / float(len(observations))
        edges[pi] = weighted

    visited = set()
    nc_group = []
    groups = []
    for pi in pis:
        final_group = []
        _visit(pi, visited, edges, final_group, threshold)
        if final_group:
            if len(final_group) == 1:
              # only a single flow in this group
              # a) it was non congested and started out in its own group
              # b) it was congested but not grouped with any other flow
              if _is_noncongested_in_all_observations(observations, final_group[0]):
                nc_group.append(final_group[0]) # case a)
              else:
                groups.append(final_group) # case b)
            else:
              groups.append(final_group)

    return nc_group, groups

# GROUPING HYSTERESIS: Implemented by not used   --------------------------------------------------------

def do_grouping_hysteresis(nc_group, groups, prev_groups):
  pass # DEAD CODE


# CONVENIENCES...   ------------------------------------------------------------

def print_config():
  print "Configuration CONGESTION_THRESHOLD({0}), HYSTERESIS_THRESHOLD({1}), LOSS_THRESHOLD({2}), PV({3}), KEYFREQ_DELTA_THRESHOLD({4}), VARIANCE_DELTA_THRESHOLD({5}), SKEWNESS_DELTA_THRESHOLD({6}), LOSS_DELTA_THRESHOLD({7})".format(
    CONGESTION_THRESHOLD, HYSTERESIS_THRESHOLD, LOSS_THRESHOLD, PV, KEYFREQ_DELTA_THRESHOLD, VARIANCE_DELTA_THRESHOLD, SKEWNESS_DELTA_THRESHOLD, LOSS_DELTA_THRESHOLD)
