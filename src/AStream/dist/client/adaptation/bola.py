__author__ = 'pjuluri'

import config_dash



class Bola(Abr):

    def __init__(self, config):
        global verbose
        global manifest

        utility_offset = -math.log(manifest.bitrates[0]) # so utilities[0] = 0
        self.utilities = [math.log(b) + utility_offset for b in manifest.bitrates]

        self.gp = config['gp']
        self.buffer_size = config['buffer_size']
        self.abr_osc = config['abr_osc']
        self.abr_basic = config['abr_basic']
        self.Vp = (self.buffer_size - manifest.segment_time) / (self.utilities[-1] + self.gp)

        self.last_seek_index = 0 # TODO
        self.last_quality = 0

        if verbose:
            for q in range(len(manifest.bitrates)):
                b = manifest.bitrates[q]
                u = self.utilities[q]
                l = self.Vp * (self.gp + u)
                if q == 0:
                    print('%d %d' % (q, l))
                else:
                    qq = q - 1
                    bb = manifest.bitrates[qq]
                    uu = self.utilities[qq]
                    ll = self.Vp * (self.gp + (b * uu - bb * u) / (b - bb))
                    print('%d %d    <- %d %d' % (q, l, qq, ll))

    def quality_from_buffer(self):
        level = get_buffer_level()
        quality = 0
        score = None
        for q in range(len(manifest.bitrates)):
            s = ((self.Vp * (self.utilities[q] + self.gp) - level) / manifest.bitrates[q])
            if score == None or s > score:
                quality = q
                score = s
        return quality

    def get_quality_delay(self, segment_index):
        global manifest
        global throughput

        if not self.abr_basic:
            t = min(segment_index - self.last_seek_index, len(manifest.segments) - segment_index)
            t = max(t / 2, 3)
            t = t * manifest.segment_time
            buffer_size = min(self.buffer_size, t)
            self.Vp = (buffer_size - manifest.segment_time) / (self.utilities[-1] + self.gp)

        quality = self.quality_from_buffer()
        delay = 0

        if quality > self.last_quality:
            quality_t = self.quality_from_throughput(throughput)
            if quality <= quality_t:
                delay = 0
            elif self.last_quality > quality_t:
                quality = self.last_quality
                delay = 0
            else:
                if not self.abr_osc:
                    quality = quality_t + 1
                    delay = 0
                else:
                    quality = quality_t
                    # now need to calculate delay
                    b = manifest.bitrates[quality]
                    u = self.utilities[quality]
                    #bb = manifest.bitrates[quality + 1]
                    #uu = self.utilities[quality + 1]
                    #l = self.Vp * (self.gp + (bb * u - b * uu) / (bb - b))
                    l = self.Vp * (self.gp + u) ##########
                    delay = max(0, get_buffer_level() - l)
                    if quality == len(manifest.bitrates) - 1:
                        delay = 0
                    # delay = 0 ###########

        self.last_quality = quality
        return (quality, delay)

    def report_seek(self, where):
        # TODO: seek properly
        global manifest
        self.last_seek_index = math.floor(where / manifest.segment_time)

    def check_abandon(self, progress, buffer_level):
        global manifest

        if self.abr_basic:
            return None

        remain = progress.size - progress.downloaded
        if progress.downloaded <= 0 or remain <= 0:
            return None

        abandon_to = None
        score = (self.Vp * (self.gp + self.utilities[progress.quality]) - buffer_level) / remain
        if score < 0:
            return # TODO: check

        for q in range(progress.quality):
            other_size = progress.size * manifest.bitrates[q] / manifest.bitrates[progress.quality]
            other_score = (self.Vp * (self.gp + self.utilities[q]) - buffer_level) / other_size
            if other_size < remain and other_score > score:
                # check size: see comment in BolaEnh.check_abandon()
                score = other_score
                abandon_to = q

        if abandon_to != None:
            self.last_quality = abandon_to

        return abandon_to


def get_buffer_level():
    global manifest
    global buffer_contents
    global buffer_fcc

    return manifest.segment_time * len(buffer_contents) - buffer_fcc


def get_buffer_level():
    global manifest
    global buffer_contents
    global buffer_fcc

    return dash_player.segment_duration * dash_player.qsize() - buffer_fcc    


buffer_size = args.max_buffer * 1000
gamma_p = args.gamma_p

parser.add_argument('-b', '--max-buffer', metavar = 'MAXBUFFER', type = float, default = 25,
                    help = 'Specify the maximum buffer size in seconds.')

parser.add_argument('-ab', '--abr-basic', action = 'store_true',
                    help = 'Set ABR to BASIC (ABR strategy dependant).')

parser.add_argument('-ao', '--abr-osc', action = 'store_true',
                    help = 'Set ABR to minimize oscillations.')

parser.add_argument('-gp', '--gamma-p', metavar = 'GAMMAP', type = float, default = 5,
                    help = 'Specify the (gamma p) product in seconds.')
parser.add_argument('-noibr', '--no-insufficient-buffer-rule', action = 'store_true',
                    help = 'Disable Insufficient Buffer Rule.')

max_buffer = 25
gamma_p = 5
abr_osc = False
abr_basic = False
no_insufficient_buffer_rule = False
buffer_size = max_buffer * 1000

config = {'buffer_size': buffer_size,
          'gp': gamma_p,
          'abr_osc': abr_osc,
          'abr_basic': abr_basic,
          'no_ibr': no_insufficient_buffer_rule}

Class bola():

    def __init__(self, verbose, config, bitrates, dash_player, weighted_dwn_rate, curr_bitrate, next_segment_sizes):

        self.bitrates = bitrates
        self.utility_offset = -math.log(self.bitrates[0]) # so utilities[0] = 0
        self.utilities = [math.log(b) + utility_offset for b in self.bitrates]

        self.gp = config['gp']
        self.buffer_size = config['buffer_size']
        self.abr_osc = config['abr_osc']
        self.abr_basic = config['abr_basic']
        self.Vp = (self.buffer_size - dash_player.segment_duration) / (self.utilities[-1] + self.gp)

        self.last_seek_index = 0 # TODO
        self.last_quality = 0


        if verbose:
            for q in range(len(self.bitrates)):
                b = self.bitrates[q]
                u = self.utilities[q]
                l = self.Vp * (self.gp + u)
                if q == 0:
                    print('%d %d' % (q, l))
                else:
                    qq = q - 1
                    bb = self.bitrates[qq]
                    uu = self.utilities[qq]
                    ll = self.Vp * (self.gp + (b * uu - bb * u) / (b - bb))
                    print('%d %d    <- %d %d' % (q, l, qq, ll))


    def quality_from_buffer():
        level = get_buffer_level()
        quality = 0
        score = None
        for q in range(len(self.bitrates)):
            s = ((self.Vp * (self.utilities[q] + self.gp) - level) / self.bitrates[q])
            if score == None or s > score:
                quality = q
                score = s
        return quality

    def get_quality_delay(self, segment_index):
        global manifest
        global throughput

        if not self.abr_basic:
            t = min(segment_index - self.last_seek_index, len(manifest.segments) - segment_index)
            t = max(t / 2, 3)
            t = t * dash_player.segment_duration
            buffer_size = min(self.buffer_size, t)
            self.Vp = (buffer_size - dash_player.segment_duration) / (self.utilities[-1] + self.gp)

        quality = self.quality_from_buffer()
        delay = 0

        if quality > self.last_quality:
            quality_t = self.quality_from_throughput(throughput)
            if quality <= quality_t:
                delay = 0
            elif self.last_quality > quality_t:
                quality = self.last_quality
                delay = 0
            else:
                if not self.abr_osc:
                    quality = quality_t + 1
                    delay = 0
                else:
                    quality = quality_t
                    # now need to calculate delay
                    b = self.bitrates[quality]
                    u = self.utilities[quality]
                    #bb = manifest.bitrates[quality + 1]
                    #uu = self.utilities[quality + 1]
                    #l = self.Vp * (self.gp + (bb * u - b * uu) / (bb - b))
                    l = self.Vp * (self.gp + u) ##########
                    delay = max(0, get_buffer_level() - l)
                    if quality == len(self.bitrates) - 1:
                        delay = 0
                    # delay = 0 ###########

        self.last_quality = quality
        return (quality, delay)

    def report_seek(self, where):
        # TODO: seek properly
        global manifest
        self.last_seek_index = math.floor(where / dash_player.segment_duration)

    def check_abandon(self, progress, buffer_level):
        global manifest

        if self.abr_basic:
            return None

        remain = progress.size - progress.downloaded
        if progress.downloaded <= 0 or remain <= 0:
            return None

        abandon_to = None
        score = (self.Vp * (self.gp + self.utilities[progress.quality]) - buffer_level) / remain
        if score < 0:
            return # TODO: check

        for q in range(progress.quality):
            other_size = progress.size * self.bitrates[q] / self.bitrates[progress.quality]
            other_score = (self.Vp * (self.gp + self.utilities[q]) - buffer_level) / other_size
            if other_size < remain and other_score > score:
                # check size: see comment in BolaEnh.check_abandon()
                score = other_score
                abandon_to = q

        if abandon_to != None:
            self.last_quality = abandon_to

        return abandon_to


def weighted_dash(bitrates, dash_player, weighted_dwn_rate, curr_bitrate, next_segment_sizes):
    """
    Module to predict the next_bitrate using the weighted_dash algorithm
    :param bitrates: List of bitrates
    :param weighted_dwn_rate:
    :param curr_bitrate:
    :param next_segment_sizes: A dict mapping bitrate: size of next segment
    :return: next_bitrate, delay
    """
    bitrates = [int(i) for i in bitrates]
    bitrates.sort()
    # Waiting time before downloading the next segment
    delay = 0
    next_bitrate = None
    available_video_segments = dash_player.buffer.qsize() - dash_player.initial_buffer
    # If the buffer is less that the Initial buffer, playback remains at th lowest bitrate
    # i.e dash_buffer.current_buffer < dash_buffer.initial_buffer
    available_video_duration = available_video_segments * dash_player.segment_duration
    config_dash.LOG.debug("Buffer_length = {} Initial Buffer = {} Available video = {} seconds, alpha = {}. "
                          "Beta = {} WDR = {}, curr Rate = {}".format(dash_player.buffer.qsize(),
                                                                      dash_player.initial_buffer,
                                                                      available_video_duration, dash_player.alpha,
                                                                      dash_player.beta, weighted_dwn_rate,
                                                                      curr_bitrate))

    if weighted_dwn_rate == 0 or available_video_segments == 0:
        next_bitrate = bitrates[0]
    # If time to download the next segment with current bitrate is longer than current - initial,
    # switch to a lower suitable bitrate

    elif float(next_segment_sizes[curr_bitrate])/weighted_dwn_rate > available_video_duration:
        config_dash.LOG.debug("next_segment_sizes[curr_bitrate]) weighted_dwn_rate > available_video")
        for bitrate in reversed(bitrates):
            if bitrate < curr_bitrate:
                if float(next_segment_sizes[bitrate])/weighted_dwn_rate < available_video_duration:
                    next_bitrate = bitrate
                    break
        if not next_bitrate:
            next_bitrate = bitrates[0]
    elif available_video_segments <= dash_player.alpha:
        config_dash.LOG.debug("available_video <= dash_player.alpha")
        if curr_bitrate >= max(bitrates):
            config_dash.LOG.info("Current bitrate is MAX = {}".format(curr_bitrate))
            next_bitrate = curr_bitrate
        else:
            higher_bitrate = bitrates[bitrates.index(curr_bitrate)+1]
            # Jump only one if suitable else stick to the current bitrate
            config_dash.LOG.info("next_segment_sizes[higher_bitrate] = {}, weighted_dwn_rate = {} , "
                                 "available_video={} seconds, ratio = {}".format(next_segment_sizes[higher_bitrate],
                                                                                 weighted_dwn_rate,
                                                                                 available_video_duration,
                                                                                float(next_segment_sizes[higher_bitrate])/weighted_dwn_rate))
            if float(next_segment_sizes[higher_bitrate])/weighted_dwn_rate < available_video_duration:
                next_bitrate = higher_bitrate
            else:
                next_bitrate = curr_bitrate
    elif available_video_segments <= dash_player.beta:
        config_dash.LOG.debug("available_video <= dash_player.beta")
        if curr_bitrate >= max(bitrates):
            next_bitrate = curr_bitrate
        else:
            for bitrate in reversed(bitrates):
                if bitrate >= curr_bitrate:
                    if float(next_segment_sizes[bitrate])/weighted_dwn_rate < available_video_duration:
                        next_bitrate = bitrate
                        break
            if not next_bitrate:
                next_bitrate = curr_bitrate

    elif available_video_segments > dash_player.beta:
        config_dash.LOG.debug("available_video > dash_player.beta")
        if curr_bitrate >= max(bitrates):
            next_bitrate = curr_bitrate
        else:
            for bitrate in reversed(bitrates):
                if bitrate >= curr_bitrate:
                    if float(next_segment_sizes[bitrate])/weighted_dwn_rate > available_video_duration:
                        next_bitrate = bitrate
                        break
        if not next_bitrate:
            next_bitrate = curr_bitrate
        delay = dash_player.buffer.qsize() - dash_player.beta
        config_dash.LOG.info("Delay:{}".format(delay))
    else:
        next_bitrate = curr_bitrate
    config_dash.LOG.debug("The next_bitrate is assigned as {}".format(next_bitrate))
    return next_bitrate, delay
