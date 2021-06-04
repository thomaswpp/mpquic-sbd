package quic

import (
    // "fmt"
    "sort"
    "encoding/csv"
    "strconv"
    "os"
    "github.com/lucas-clemente/quic-go/internal/protocol"
)

var (
  sess *session
  newFile  = [10]bool{true, true, true, true, true, true, true, true, true, true}
  newFile2 = [10]bool{true, true, true, true, true, true, true, true, true, true}
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

type diffStats struct {
  diffSkew        float64
  diffVar         float64
  diffFreq        float64
  diffPktLoss     float64
  limitPktLoss    float64
  limitVarEst     float64
}

type FlowGroups struct {
  pathID []protocol.PathID
  diffStats []*diffStats
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

    fg.diffStats = make([]*diffStats, 1 + max(fg.pathID))

    for k, _ := range fg.diffStats {
      fg.diffStats[k] = &diffStats{
              diffSkew: 0,
              diffVar:  0,
              diffFreq: 0,
              diffPktLoss: 0,
              limitPktLoss: 0,
              limitVarEst:  0,
        }
    }

    sess = s
}

func (fg * FlowGroups) addFlow(pathID protocol.PathID) {
    fg.pathID = append(fg.pathID, pathID)
}

func (fg * FlowGroups) makeDiffStats(n int) {
  fg.diffStats = make([]*diffStats, n)
}

func writeCsv(filename string, row []string) {

    file, err := os.OpenFile(filename, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
    defer file.Close()

    if err != nil {
        os.Exit(1)
    }

    csvwriter := csv.NewWriter(file)
    // for _, row := range rows {
    //     _ = csvwriter.Write(row)
    // }
    _ = csvwriter.Write(row)

    if err := csvwriter.Error(); err != nil {
        os.Exit(1)
    }

    csvwriter.Flush()

    file.Close()
}


func (fg * FlowGroups) PrintFile() {


      for _, k := range fg.pathID {

        name_file := "dados/diff" + strconv.Itoa(int(k)) + ".csv"

        if newFile[k] {
            newFile[k] = false
            
            row := []string{
                  "DiffSkewEst", 
                  "DiffVarEst", 
                  "DiffFreqEst",
                  "DiffPktLoss",
                  "limitVarEst",
                  "limitPktLoss",
            }
            writeCsv(name_file, row)
        }

        row := []string{
            strconv.FormatFloat(fg.diffStats[k].diffSkew, 'f', -1, 64),
            strconv.FormatFloat(fg.diffStats[k].diffVar, 'f', -1, 64),
            strconv.FormatFloat(fg.diffStats[k].diffFreq, 'f', -1, 64),
            strconv.FormatFloat(fg.diffStats[k].diffPktLoss, 'f', -1, 64),
            strconv.FormatFloat(fg.diffStats[k].limitVarEst, 'f', -1, 64),
            strconv.FormatFloat(fg.diffStats[k].limitPktLoss, 'f', -1, 64),
        }
        writeCsv(name_file, row)
      }
}

func (fg * FlowGroups) PrintGroupsFile(m map[protocol.PathID]uint8) {

      for k, id := range m {

          name_file := "dados/group" + strconv.Itoa(int(k)) + ".csv"

          if newFile2[k] {
              newFile2[k] = false
              
              row := []string{
                    "PathID", 
                    "Classifier", 
              }
              writeCsv(name_file, row)
          }

          row := []string{
              strconv.Itoa(int(k)),
              strconv.Itoa(int(id)),
          }
          writeCsv(name_file, row)
      }
}

// SBD GROUPING ALGORITHM -------------------------------------------------------

func (fg *FlowGroups) splitCongestion(congested *FlowGroups, notCongested *FlowGroups){
    var isSharing bool
    congested.makeDiffStats(1 + max(fg.pathID))
    notCongested.makeDiffStats(1 + max(fg.pathID))

    for _ , k := range fg.pathID {
        isSharing = false
        // fmt.Println("Entrou: ", k, sess.paths[k].pstats.Skewness.GetSkewEst(), sess.paths[k].pstats.Loss.GetPacketLoss())
        
        if (( sess.paths[k].pstats.Skewness.GetSkewEst() < CONGESTION_THRESHOLD ) || 
            ( sess.paths[k].pstats.Skewness.GetSkewEst() < HYSTERESIS_THRESHOLD && sess.paths[k].pstats.PB ) || 
            ( sess.paths[k].pstats.Loss.GetPacketLoss() > LOSS_THRESHOLD )) {

            isSharing = true
            congested.addFlow(k)
            congested.diffStats[k] = fg.diffStats[k]
        } else {
            notCongested.addFlow(k)
            congested.diffStats[k] = fg.diffStats[k]
        }
        sess.paths[k].pstats.PB = isSharing
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

    paths.makeDiffStats(1 + max(fg.pathID))
    id := fg.pathID[0]
    paths.addFlow(id)
    paths.diffStats[id] = fg.diffStats[id]

    for i, k := range fg.pathID[1:n] {

        k_prev := fg.pathID[i]

        switch key {
      	case "freq":
      		    diff = sess.paths[k_prev].pstats.Freq.GetFreqEst() - sess.paths[k].pstats.Freq.GetFreqEst()
              fg.diffStats[k].diffFreq = diff
      	case "var":
      		    diff = sess.paths[k_prev].pstats.Variance.GetVarEst() - sess.paths[k].pstats.Variance.GetVarEst()
              fg.diffStats[k].diffVar = diff
              currThresh = sess.paths[k_prev].pstats.Variance.GetVarEst() * deltaThresh  // 2. relative to first in the CURRENT GROUP (LCN'14)
              fg.diffStats[k].limitVarEst = currThresh
        case "skew":
              diff = sess.paths[k_prev].pstats.Skewness.GetSkewEst() - sess.paths[k].pstats.Skewness.GetSkewEst()              
              fg.diffStats[k].diffSkew = diff
      	default: //loss
              diff = sess.paths[k_prev].pstats.Loss.GetPacketLoss() - sess.paths[k].pstats.Loss.GetPacketLoss()
              fg.diffStats[k].diffPktLoss = diff
              // fmt.Printf("loss: %d %f\n", k, diff)
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
            cpyPaths.diffStats = make([]*diffStats, len(paths.diffStats))
            copy(cpyPaths.pathID, paths.pathID)
            copy(cpyPaths.diffStats, paths.diffStats)

            *groups = append(*groups, cpyPaths)
            //new group
            paths.pathID = paths.pathID[:0]
            paths.addFlow(k)
        }
        paths.diffStats[k] = fg.diffStats[k]
    }
    //deep copy
    cpyPaths := paths
    cpyPaths.pathID = make([]protocol.PathID, len(paths.pathID))
    cpyPaths.diffStats = make([]*diffStats, len(paths.diffStats))
    copy(cpyPaths.pathID, paths.pathID)
    copy(cpyPaths.diffStats, paths.diffStats)
    *groups = append(*groups, cpyPaths)
}

func (fg *FlowGroups) splitSkewness(localGroupsSkewness *[]FlowGroups) {
    var hasHighLoss = false

    for _, k := range fg.pathID {
        if sess.paths[k].pstats.Loss.GetPacketLoss() > LOSS_THRESHOLD {
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

    // fmt.Println("notCongested: ", notCongested)
    // fmt.Println("congested: ", congested)

    if (len(congested.pathID) == 0) {
        return;
    }

    congested.splitFlows(&groupsFreq, "freq", KEYFREQ_DELTA_THRESHOLD, 'a')

    // fmt.Println("freq: ", groupsFreq)
    for i, _ := range groupsFreq {
        var localGroupsVariance = []FlowGroups{}
        groupsFreq[i].splitFlows(&localGroupsVariance,  "var", VARIANCE_DELTA_THRESHOLD, 'p')
        groupsVar = append(groupsVar, localGroupsVariance)
    }

    // fmt.Println("var: ", groupsVar)

    for _, groups := range groupsVar {
        for _, flows := range groups {            
            var localGroupsSkewness = []FlowGroups{}
            flows.splitSkewness(&localGroupsSkewness)
            // fmt.Println("Flowskew: ", localGroupsSkewness)
            *groupsSkewness = append(*groupsSkewness, localGroupsSkewness)
        }
    }
    // fmt.Println("Flowskew2: ", groupsSkewness)

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
      return sess.paths[k1].pstats.Skewness.GetSkewEst() > sess.paths[k2].pstats.Skewness.GetSkewEst()
    })
}

func (fg *FlowGroups) sortFlowByVariance() {

    sort.Slice(fg.pathID, func(i, j int) bool {
      k1 := fg.pathID[i]
      k2 := fg.pathID[j]
      return sess.paths[k1].pstats.Variance.GetVarEst() > sess.paths[k2].pstats.Variance.GetVarEst()
    })
}

func (fg *FlowGroups) sortFlowByFreq() {

    sort.Slice(fg.pathID, func(i, j int) bool {
      k1 := fg.pathID[i]
      k2 := fg.pathID[j]
      return sess.paths[k1].pstats.Freq.GetFreqEst() > sess.paths[k2].pstats.Freq.GetFreqEst()
    })
}

func (fg *FlowGroups) sortFlowByLoss() {

    sort.Slice(fg.pathID, func(i, j int) bool {
      k1 := fg.pathID[i]
      k2 := fg.pathID[j]
      return sess.paths[k1].pstats.Loss.GetPacketLoss() > sess.paths[k2].pstats.Loss.GetPacketLoss()
    })
}

func (fg *FlowGroups) FlowGroups(s *session) ([][]FlowGroups) {

    var groupsSkewness = [][]FlowGroups{}

    fg.setup(s)

    fg.processOwds(&groupsSkewness)

    return groupsSkewness
}
