package quic

import (
	"fmt"
	"time"
	"sort"
	"encoding/json"
	"github.com/lucas-clemente/quic-go/internal/protocol"
)


//SBD 
type Loss struct {
	lossCount uint8
	pathID protocol.PathID
}

type Sbd struct {
   owd float64
   p *path
   lossCount []Loss
   ts_rcv time.Time
}


type group map[protocol.PathID]uint8

const (
	SBD_N      uint64  		    = 50
	SBD_M      uint64  		    = 50
	SBD_MAX_OBSERVATIONS int    = 10	
)

//SBD Vars
var ( 
	mgroupsObservation 		[SBD_MAX_OBSERVATIONS]group
	tempoDecorrente 		float64
	tempo 					time.Time 
	sbdEpoch 				uint16

	//SBD groups
	flowGroups 				FlowGroups
	groupsSBD 				[][]FlowGroups

	//acuracy
	sbd_accuracy			float64
	sbd_count_acc			float64
	sbd_count_equal         float64
	sbd_count_diff          float64

	//acuracy
	sbd_accuracy_2			float64
	sbd_count_acc_2			float64
	sbd_count_equal_2       float64
	sbd_count_diff_2        float64

	sbdChanStruct = make(chan Sbd, 1000)
	groupChan     = make(chan bool, 100)

)


func stringToArray(str string) ([]int, error) {
	
	var b []int
	err := json.Unmarshal([]byte(str), &b)
    return b, err
 }

 func arrayToString(a map[protocol.PathID]uint8) string {
    
    var b []int

    keys := make([]int, 0, len(a))
    for k := range a {
        keys = append(keys, int(k))
    }
    sort.Ints(keys)

    for _, k := range keys {
        b = append(b, int(a[protocol.PathID(k)]))
    }

    if b[0] == 2 && b[1] == 1 {
        sort.Ints(b)
    }

    fmt.Println(b)

    s, _ := json.Marshal(b)
    return string(s)
}

func copyPaths(s *session) ([]protocol.PathID) {

	var arrPi []protocol.PathID
	s.pathsLock.RLock()
  	for pi, _ := range s.paths {
	      if pi != 0 {
	        arrPi = append(arrPi, pi)
	      }
    }
    s.pathsLock.RUnlock()
    return arrPi
}

func computeAccuracy(s *session) {
		count           := 0
		congested       := false
		var arr [3]int
	
		fmt.Println("Begin computeAccuracy: =================")
		s.pathsLock.RLock()
		for pi, path := range s.paths {
			if pi == 0 {
				continue
			}
			g := path.group
			arr[g]++
			fmt.Println("Path: ", pi, g)
		}
		s.pathsLock.RUnlock()

		for _, a := range arr[1:] {
			if a != 0 {
				congested = true
			}
			if a >= 2 {
				count++
			}
		}

		fmt.Println("Freq: ", arr)
		switch count {
			case 0:
					sbd_count_diff++
			case 1:
					sbd_count_equal++
		}

		nsb_acc := sbd_count_diff / (sbd_count_equal + sbd_count_diff)
		now := time.Now()
		fmt.Println("NSB Accuracy - ", now, " - ", nsb_acc, sbd_count_diff, sbd_count_equal, sbd_count_diff)

		if congested {
				sbd_count_acc++
				if count >= 1 {
					sbd_accuracy++
				}
				sb_acc := sbd_accuracy/sbd_count_acc
				fmt.Println("SB Accuracy - ", now, " - ", sb_acc, sbd_accuracy, sbd_count_acc)
		}
		fmt.Println("End computeAccuracy: =================")
}

func (sbd *Sbd) mergeObservations(s *session) {
	
	var groupWin string
	mgroups := make(map[string]int)
	max := 0	
	is_tied := false

	arrPi := copyPaths(s)

	// Count the number of times a group has been classified
	for i, _ := range mgroupsObservation {

		groupString := arrayToString(mgroupsObservation[i])
		mgroups[groupString]++
	}


	//Choose the group that appears most
	for gstr, i := range mgroups {

		// is even?
		if len(mgroups) == 2 && i == 5 {
			is_tied = true
		}

		if i > max {
			max = i
			groupWin = gstr
		}
	}

	if is_tied {
		groupWin = "[1,1]"
	}

	fmt.Println("Group WIN: ", groupWin)

	groupWinArray, _ := stringToArray(groupWin)

	for i, group := range groupWinArray {
			if len(arrPi) > 1 {
				pi := arrPi[i]
				s.paths[pi].group = uint8(group)
				s.paths[pi].epoch = sbdEpoch
			}
	}

	computeAccuracy(s)	

}

func (sbd *Sbd) grouping(s *session) {

	var sbdObservationsCount int

	for {

		<- groupChan
			

		var mgroup = make(group, 20)

		var flowGroups FlowGroups

		groupsSBD = flowGroups.FlowGroups(s)

		//create all path in mpgroup
		s.pathsLock.RLock()
		for pi, _ := range s.paths {
			if pi == 0 {
				continue
			}
			mgroup[pi] = 0
		}
		s.pathsLock.RUnlock()

		// sbdEpoch++
		//classify each path
		for i, groups := range groupsSBD {
			for _, flow := range groups {
				for _, path := range flow.pathID {
					mgroup[path] 		= uint8(i+1)
				}
			}
		}

		mgroupsObservation[sbdObservationsCount] = mgroup
		sbdObservationsCount++	

		if sbdObservationsCount == SBD_MAX_OBSERVATIONS {
			sbdEpoch++
			sbdObservationsCount = 0			
			sbd.mergeObservations(s)
		}

	}
		
}

func (sbd *Sbd) computeSBD(s *session) { 



	
	for {

		params := <-sbdChanStruct


		if (s.state) {

			s.state = false
			s.saveTsRcv1 = true
			s.tsRcv = params.ts_rcv
			

			//create all path in mpgroup
			s.pathsLock.RLock()
			for pi, p := range s.paths {
				if pi == 0 {
					continue
				}
				p.pstats.ComputeStatistics(s.numberInterval)
			}
			s.pathsLock.RUnlock()			
			
			if s.numberInterval >= 2*SBD_M { // >= N	

				groupChan <- true

			}

		}

		params.p.pstats.ComputeStatisticsBase(params.owd, s.numberInterval)
		// we just want to iterate once, but sometimes can iterate twice or more
		for _, losses := range params.lossCount {
			tmpPth := s.paths[losses.pathID]
			tmpPth.pstats.ComputePacketLoss(uint64(losses.lossCount))
		}
		
	}

}
