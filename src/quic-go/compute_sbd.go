package quic

import (
	"fmt"
	"time"
	"sort"
	"encoding/json"
	// "strings"
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
   diffTsRcv time.Time
}


type group map[protocol.PathID]uint8

const (
	//SBD_T_INTERVAL float64 		 = 350.0
	SBD_N      uint64  		    = 50
	SBD_M      uint64  		    = 50
	SBD_MAX_OBSERVATIONS int    = 10	
	// SBD_TIME_OUTLIER float64    = 30.0
	// MAX_NUMBER_PATH_ID int		 = 5
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

// func swap(arr*[MAX_NUMBER_PATH_ID] int, i int, j int) {

// 	c := arr[i]
// 	arr[i] = arr[j]
// 	arr[j] = c
// }

// func selectionSort(arr*[MAX_NUMBER_PATH_ID] int) {
// 	min_idx := 0
// 	for i, _ := range arr {
		
// 		min_idx = i

// 		for j := i + 1; j < len(arr); j++ {
// 			if arr[j] < arr[min_idx] {
// 				min_idx = j
// 			}
// 		}

// 		swap(arr, min_idx, i)
// 	}


// }

func stringToArray(str string) ([]int, error) {
	
	var b []int
	err := json.Unmarshal([]byte(str), &b)
    // fmt.Println("%v", b)
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

// func arrayToString(a map[protocol.PathID]uint8) string {
	
// 	var b []int
// 	for _, g := range a {
// 		b = append(b, int(g))
// 	}	

// 	if b[0] == 2 && b[1] == 1 {
// 		sort.Ints(b)
// 	}

// 	fmt.Println(b)

// 	s, _ := json.Marshal(b)
// 	// fmt.Println(string(s))
// 	return string(s)
// }

// func arrayToString(a map[protocol.PathID]uint8, delim string) string {
	
// 	var b [MAX_NUMBER_PATH_ID]int
// 	for pi, g := range a {
// 		b[pi] = int(g)
// 	}	
//     return strings.Trim(strings.Replace(fmt.Sprint(b), " ", delim, -1), "[]")
//     //return strings.Trim(strings.Join(strings.Split(fmt.Sprint(a), " "), delim), "[]")
//     //return strings.Trim(strings.Join(strings.Fields(fmt.Sprint(a)), delim), "[]")
// }



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


func computeAccuracy2(mgroup group) {

	mode  		:= 1 // 0 - shared, 1 - non-shared
	count 		:= 0
	congested 	:= false
	var arr [3]int 

	
	for p, g := range mgroup {

		if p == 0 {
			continue
		}
		arr[g]++
		fmt.Println("Path: ", p, g)
	}
	
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
			sbd_count_diff_2++
		case 1:
			sbd_count_equal_2++		
	}

	nsb_acc := sbd_count_diff_2 / (sbd_count_equal_2 + sbd_count_diff_2)
	now := time.Now()
	fmt.Println("General Accuracy - ", now, " - ", nsb_acc, sbd_count_equal_2, sbd_count_diff_2)

	if congested {
		sbd_count_acc_2++
		//mode non-shared
		if (mode == 1) {
			if count == 0 {
				sbd_accuracy_2++
			}

		} else { //shared
			if count >= 1 {
				sbd_accuracy_2++
			}
		}
		now := time.Now()		
		fmt.Println("Accuracy - ", now, " - ", sbd_accuracy_2/sbd_count_acc_2, sbd_accuracy_2, sbd_count_acc_2)
	}

}

func computeAccuracy(s *session) {

	mode  		:= 0 // 0 - shared, 1 - non-shared
	count 		:= 0
	congested 	:= false
	var arr [3]int 


	fmt.Println("Merge: =================")

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
	fmt.Println("General Accuracy - ", now, " - ", nsb_acc, sbd_count_equal, sbd_count_diff)

	if congested {
		sbd_count_acc++
		//mode non-shared
		if (mode == 1) {
			// if count == 0 {
			// 	sbd_accuracy++
			// }

		} else { //shared
			if count >= 1 {
				sbd_accuracy++
			}
		}		
		fmt.Println("Accuracy - ", now, " - ", sbd_accuracy/sbd_count_acc, sbd_accuracy, sbd_count_acc)
	}
	fmt.Println("Fim Merge: =================")
}

// func (sbd *Sbd) mergeObservations(s *session) {

// 	var together[20][10]uint8

// 	// Count the number of times a pathid has been classified by a group
// 	for i, _ := range mgroupsObservation {

// 		for pi, group := range mgroupsObservation[i] {
			
// 			together[int(pi)][int(group)]++
// 		}
// 	}


// 	//Choose the group that appears most
// 	for pi, _ := range mgroupsObservation[0] {
		
// 		if pi == 0 {
// 			continue
// 		}

// 		i     := int(pi)
// 		group := 0
// 		max   := -1

// 		for j := 0; j < int(SBD_MAX_OBSERVATIONS); j++ {
		
// 			count := int(together[i][j])

// 			if  count > max {
// 				max = count
// 				group = j
// 			}

// 		}
		
// 		//update groups
// 		// s.pathsLock.RLock()

// 		s.paths[pi].group = uint8(group)
// 		s.paths[pi].epoch = sbdEpoch
		
// 		// s.pathsLock.RUnlock()
// 	}

// 	computeAccuracy(s)	

// }

func (sbd *Sbd) mergeObservations2(s *session) {
	
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

				
		// fmt.Println("==============================================================================================", s.numberInterval)
		// fmt.Println(sbdEpoch, time.Now())
		groupsSBD = flowGroups.FlowGroups(s)
		

		// fmt.Println("gruops: ", groupsSBD)
		// flowGroups.PrintFile()

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
					// fmt.Printf("fi: %d %d\n", path, uint8(i+1))
					mgroup[path] 		= uint8(i+1)
					// s.paths[path].group = uint8(i+1)
					// s.paths[path].epoch = sbdEpoch
				}
			}
		}

		// computeAccuracy2(mgroup)

		mgroupsObservation[sbdObservationsCount] = mgroup
		sbdObservationsCount++	

		// flowGroups.PrintGroupsFile(mgroup)

		if sbdObservationsCount == SBD_MAX_OBSERVATIONS {
			sbdEpoch++
			sbdObservationsCount = 0			
			// sbd.mergeObservations(s)
			sbd.mergeObservations2(s)
		}

	}
		
}

func (sbd *Sbd) computeSBD(s *session) { 

	// timeDelay := tempoDecorrente	
	// var state bool
	// var is_group bool
	var state_owd = false
	// var is_350 = false
	// var count_metrics = 0




	if params.diffTsRcv >= SBD_T_INTERVAL {
		if s.tsRcv.Sub(s.tsRcv1) <= 20 {
			for _, p := range s.paths {
				p.pstats.Restart()
			}
			s.state = false
		}
	}

	
	for {

		params := <-sbdChanStruct
		//every T_INTERVAL compute path statistics sbd
		// if s.timeIntervalSBD > SBD_T_INTERVAL {
			
			// state = true
		// 	is_time = true

		// 	s.timeIntervalSBD = 0
		// 	s.numberInterval += 1		
		// }


		if (s.state) {

			// is_350 = true
			// count_metrics = 0
			s.state = false
			s.saveTsRcv1 = true
			

			//create all path in mpgroup
			s.pathsLock.RLock()
			for pi, p := range s.paths {
				if pi == 0 {
					continue
				}
				p.pstats.ComputeStatistics(s.numberInterval)
			}
			s.pathsLock.RUnlock()			
			
			
			// p.pstats.PrintFile(p.pathID)

			if s.numberInterval >= 2*SBD_M { // >= N	

				// is_group = true
				groupChan <- true

			}

		}

		if params.owd < SBD_T_INTERVAL {

			// count_metrics += 1
			//SBD - compute statistics base	
			params.p.pstats.ComputeStatisticsBase(params.owd, s.numberInterval)
			// we just want to iterate once, but sometimes can iterate twice or more
			for _, losses := range params.lossCount {
				tmpPth := s.paths[losses.pathID]
				tmpPth.pstats.ComputePacketLoss(uint64(losses.lossCount))
			}

			// state_owd = false

		} else {
			// if count_metrics <= 2 && is_350 {
			// 	//to_discard
			// 	for _, p := range s.paths {
			// 		p.pstats.Restart()
			// 	}
			// 	is_350 = false
			// }
			// state_owd = true
		}

		
		// if is_350 {
		// 	now := time.Now()
		// 	s.pathsLock.RLock()
		// 	for pi, p := range s.paths {
		// 		if pi == 0 {
		// 			continue
		// 		}
		// 		p.pstats.PrintFileOWD(now, p.pathID, params.owd, is_350, is_group)
		// 	}
		// 	s.pathsLock.RUnlock()
		// 	is_350 = false
		// 	is_group = false
		// } else {
		// 	now := time.Now()
		// 	params.p.pstats.PrintFileOWD(now, params.p.pathID, params.owd, is_350, is_group)
		// }

		
	}

}
