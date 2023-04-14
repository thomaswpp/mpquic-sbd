package quic

import (
    "sort"
    "time"
    "github.com/lucas-clemente/quic-go/internal/protocol"
)

const (
    CONGESTION_THRESHOLD        float64 = 0.1  // c_s
    KEYFREQ_DELTA_THRESHOLD     float64 = 0.1  // p_f
    LOSS_DELTA_THRESHOLD        float64 = 0.1  // p_d (difference in subflows' loss to be in same group)
    SKEWNESS_DELTA_THRESHOLD    float64 = 0.15 // p_s
    VARIANCE_DELTA_THRESHOLD    float64 = 0.1  // p_mad
    F                           float64 = 20
    HYSTERESIS_THRESHOLD        float64 = 0.3 // c_h
    LOSS_THRESHOLD              float64 = 0.1 // p_l
)

type timeTD struct {
    td time.Time
    tr time.Time
    tr1 time.Time

}

type statistics struct {

    meanOWD float64
    meandelay float64
    skewness float64
    varest float64
    freqest float64
    loss float64
    PB bool

}


type FlowGroups struct {
  pathID []protocol.PathID
  statistics []*statistics
  timeTD *timeTD
}

func max(arr []protocol.PathID) (int) {
  max := 0

  for _, k := range arr {
    if int(k) > max {
      max = int(k)
    }
  }
  return max
}

func (fg *FlowGroups) setup(s *session) {


    for pi, _ := range s.paths {
      if pi != 0 {
          fg.pathID = append(fg.pathID, pi)
      }
    }


    fg.statistics = make([]*statistics, 1 + max(fg.pathID))

    fg.timeTD = &timeTD{
          td: s.timeStart,
          tr:  s.tsRcv,
          tr1: s.tsRcv1,
    }

    for k, _ := range fg.statistics {

        fg.statistics[k] = &statistics {
            meanOWD:  0,
            meandelay: 0,
            skewness: 0,
            varest: 0,
            freqest: 0,
            loss: 0,
            PB: false,
        }
    }

    for _, i := range fg.pathID {



        meanOWD := s.paths[i].pstats.MeanOwd.GetMeanOwd() 
        meandelay := s.paths[i].pstats.MeanDelay.GetMeanDelay()
        skewness := s.paths[i].pstats.Skewness.GetSkewEst()
        varest := s.paths[i].pstats.Variance.GetVarEst()
        freqest := s.paths[i].pstats.Freq.GetFreqEst()
        loss := s.paths[i].pstats.Loss.GetPacketLoss()


        fg.statistics[i] = &statistics {
            meanOWD:  meanOWD,
            meandelay: meandelay,
            skewness: skewness,
            varest: varest,
            freqest: freqest,
            loss: loss,
            PB: false,
        }
    }


}

func (fg * FlowGroups) addFlow(pathID protocol.PathID) {
    fg.pathID = append(fg.pathID, pathID)
}

func (fg * FlowGroups) makeStatsArray(n int) {
  fg.statistics = make([]*statistics, n)
}

// SBD GROUPING ALGORITHM -------------------------------------------------------

func (fg *FlowGroups) splitCongestion(congested *FlowGroups, notCongested *FlowGroups){
    var isSharing bool
    congested.makeStatsArray(1 + max(fg.pathID))
    notCongested.makeStatsArray(1 + max(fg.pathID))

    for _ , k := range fg.pathID {
        isSharing = false
        
        if (( fg.statistics[k].skewness < CONGESTION_THRESHOLD ) || 
            ( fg.statistics[k].skewness < HYSTERESIS_THRESHOLD && fg.statistics[k].PB) || 
            ( fg.statistics[k].loss > LOSS_THRESHOLD )) {

            isSharing = true
            congested.addFlow(k)
            congested.statistics[k] = fg.statistics[k]
        } else {
            notCongested.addFlow(k)
            congested.statistics[k] = fg.statistics[k]
        }
        fg.statistics[k].PB = isSharing
    }
}

func (fg *FlowGroups) splitFlows(groups *[]FlowGroups, key string, deltaThresh float64, flag byte) {

    var paths FlowGroups
    var diff, currThresh float64
    var belongsLastGroup bool
    n := len(fg.pathID)

    if n == 0 {
        return;
    }

    fg.sortFlows(key)

    paths.makeStatsArray(1 + max(fg.pathID))
    id := fg.pathID[0]
    paths.addFlow(id)
    paths.statistics[id] = fg.statistics[id]

    for i, k := range fg.pathID[1:n] {

        k_prev := fg.pathID[i]

        switch key {
      	case "freq":
      		  diff = fg.statistics[k_prev].freqest - fg.statistics[k].freqest
      	case "var":
      		  diff = fg.statistics[k_prev].varest - fg.statistics[k].varest
              currThresh = fg.statistics[k_prev].varest * deltaThresh  // 2. relative to first in the CURRENT GROUP (LCN'14)
        case "skew":
              diff = fg.statistics[k_prev].skewness - fg.statistics[k].skewness             
      	default: //loss
              diff =  fg.statistics[k_prev].loss - fg.statistics[k].loss
      	}

        belongsLastGroup = false
        if flag == 'a' {
            if diff < deltaThresh {
                belongsLastGroup = true
            }
        } else if flag == 'p' {
                // 2. relative to first in the CURRENT GROUP (LCN'14)
              if diff < currThresh {
                  belongsLastGroup = true
              }
        }

        if belongsLastGroup {
            paths.addFlow(k)
        } else {
            //deep copy
            cpyPaths := paths
            cpyPaths.pathID = make([]protocol.PathID, len(paths.pathID))
            cpyPaths.statistics = make([]*statistics, len(paths.statistics))
            copy(cpyPaths.pathID, paths.pathID)            
            copy(cpyPaths.statistics, paths.statistics)

            *groups = append(*groups, cpyPaths)
            //new group
            paths.pathID = paths.pathID[:0]
            paths.addFlow(k)
        }
        paths.statistics[k] = fg.statistics[k]
    }
    //deep copy
    cpyPaths := paths
    cpyPaths.pathID = make([]protocol.PathID, len(paths.pathID))
    cpyPaths.statistics = make([]*statistics, len(paths.statistics))
    copy(cpyPaths.pathID, paths.pathID)
    copy(cpyPaths.statistics, paths.statistics)
    *groups = append(*groups, cpyPaths)
}

func (fg *FlowGroups) splitSkewness(localGroupsSkewness *[]FlowGroups) {
    var hasHighLoss = false

    for _, k := range fg.pathID {
        if fg.statistics[k].loss > LOSS_THRESHOLD {
            hasHighLoss = true
            break
        }
    }

    if hasHighLoss {
        fg.splitFlows(localGroupsSkewness, "loss", LOSS_DELTA_THRESHOLD, 'a')
    } else {
        fg.splitFlows(localGroupsSkewness, "skew", SKEWNESS_DELTA_THRESHOLD, 'a')
    }
}


func (fg *FlowGroups) processOwds(groupsSkewness *[][]FlowGroups){
    var groupsFreq = []FlowGroups{}
    var groupsVar  = [][]FlowGroups{}
    var congested, notCongested FlowGroups

    fg.splitCongestion(&congested, &notCongested)

    if (len(congested.pathID) == 0) {
        return;
    }

    congested.splitFlows(&groupsFreq, "freq", KEYFREQ_DELTA_THRESHOLD, 'a')

    for i, _ := range groupsFreq {
        var localGroupsVariance = []FlowGroups{}
        groupsFreq[i].splitFlows(&localGroupsVariance,  "var", VARIANCE_DELTA_THRESHOLD, 'p')
        groupsVar = append(groupsVar, localGroupsVariance)
    }

    for _, groups := range groupsVar {
        for _, flows := range groups {            
            var localGroupsSkewness = []FlowGroups{}
            flows.splitSkewness(&localGroupsSkewness)
            *groupsSkewness = append(*groupsSkewness, localGroupsSkewness)
        }
    }

}

func (fg *FlowGroups) sortFlows(key string) {

    switch key {
    case "freq":
          fg.sortFlowByFreq()
    case "var":
          fg.sortFlowByVariance()
      case "skew":
          fg.sortFlowBySkewness()
    default: //loss
          fg.sortFlowByLoss()
    }
}

func (fg *FlowGroups) sortFlowBySkewness() {

    sort.Slice(fg.pathID, func(i, j int) bool {
      k1 := fg.pathID[i]
      k2 := fg.pathID[j]
      return fg.statistics[k1].skewness > fg.statistics[k2].skewness
    })
}

func (fg *FlowGroups) sortFlowByVariance() {

    sort.Slice(fg.pathID, func(i, j int) bool {
      k1 := fg.pathID[i]
      k2 := fg.pathID[j]
      return fg.statistics[k1].varest > fg.statistics[k2].varest
    })
}

func (fg *FlowGroups) sortFlowByFreq() {

    sort.Slice(fg.pathID, func(i, j int) bool {
      k1 := fg.pathID[i]
      k2 := fg.pathID[j]
      return fg.statistics[k1].freqest > fg.statistics[k2].freqest
    })
}

func (fg *FlowGroups) sortFlowByLoss() {

    sort.Slice(fg.pathID, func(i, j int) bool {
      k1 := fg.pathID[i]
      k2 := fg.pathID[j]
      return fg.statistics[k1].loss > fg.statistics[k2].loss
    })
}

func (fg *FlowGroups) FlowGroups(s *session) ([][]FlowGroups) {

    var groupsSkewness = [][]FlowGroups{}
    
    fg.setup(s)

    fg.processOwds(&groupsSkewness)

    return groupsSkewness
}
