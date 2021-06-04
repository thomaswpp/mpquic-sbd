package quic

import (
	"fmt"
	"time"
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
}


type group map[protocol.PathID]uint8

const (
	SBD_T_INTERVAL float64 		 = 350.0
	SBD_N      uint64  		     = 50
	SBD_M      uint64  		     = 50
	SBD_MAX_OBSERVATIONS int     = 10	
	SBD_TIME_OUTLIER float64     = 30.0
	MAX_NUMBER_PATH_ID int		 = 5
)

//SBD Vars
var ( 
	mgroupsObservation 		[SBD_MAX_OBSERVATIONS]group
	tempoDecorrente 		float64
	tempo 					time.Time 
	sbdEpoch 				uint16

	pathIDCpy 				[]protocol.PathID

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
    // fmt.Println("%v", b)
    return b, err
 }

func arrayToString(a map[protocol.PathID]uint8) string {
	
	var b [MAX_NUMBER_PATH_ID]int
	for pi, g := range a {
		b[pi] = int(g)
	}	

	s, _ := json.Marshal(b)
	// fmt.Println(string(s))
	return string(s)
}

// func arrayToString(a map[protocol.PathID]uint8, delim string) string {
	
// 	var b [MAX_NUMBER_PATH_ID]int
// 	for pi, g := range a {
// 		b[pi] = int(g)
// 	}	
//     return strings.Trim(strings.Replace(fmt.Sprint(b), " ", delim, -1), "[]")
//     //return strings.Trim(strings.Join(strings.Split(fmt.Sprint(a), " "), delim), "[]")
//     //return strings.Trim(strings.Join(strings.Fields(fmt.Sprint(a)), delim), "[]")
// }



func (sbd *Sbd) setup(s *session) {

  	for pi, _ := range s.paths {
	      if pi != 0 {
	        pathIDCpy = append(pathIDCpy, pi)
	      }
    }
    fmt.Println("Vetor: ", pathIDCpy)
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
	fmt.Println("General Accuracy: ", nsb_acc, sbd_count_equal_2, sbd_count_diff_2)

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
		fmt.Println("Accuracy: ", sbd_accuracy_2/sbd_count_acc_2, sbd_accuracy_2, sbd_count_acc_2)
	}

}

func computeAccuracy(s *session) {

	mode  		:= 1 // 0 - shared, 1 - non-shared
	count 		:= 0
	congested 	:= false
	var arr [3]int 


	fmt.Println("Merge: =================")

	// s.pathsLock.RLock()
	for pi, path := range s.paths {

		if pi == 0 {
			continue
		}
		g := path.group
		arr[g]++
		fmt.Println("Path: ", pi, g)
	}
	// s.pathsLock.RUnlock()
	
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
	fmt.Println("General Accuracy: ", nsb_acc, sbd_count_equal, sbd_count_diff)

	if congested {
		sbd_count_acc++
		//mode non-shared
		if (mode == 1) {
			if count == 0 {
				sbd_accuracy++
			}

		} else { //shared
			if count >= 1 {
				sbd_accuracy++
			}
		}		
		fmt.Println("Accuracy: ", sbd_accuracy/sbd_count_acc, sbd_accuracy, sbd_count_acc)
	}
	fmt.Println("Fim Merge: =================")
}

func (sbd *Sbd) mergeObservations(s *session) {

	var together[20][10]uint8

	// Count the number of times a pathid has been classified by a group
	for i, _ := range mgroupsObservation {

		for pi, group := range mgroupsObservation[i] {
			
			together[int(pi)][int(group)]++
		}
	}


	//Choose the group that appears most
	for pi, _ := range mgroupsObservation[0] {
		
		if pi == 0 {
			continue
		}

		i     := int(pi)
		group := 0
		max   := -1

		for j := 0; j < int(SBD_MAX_OBSERVATIONS); j++ {
		
			count := int(together[i][j])

			if  count > max {
				max = count
				group = j
			}

		}
		
		//update groups
		// s.pathsLock.RLock()

		s.paths[pi].group = uint8(group)
		s.paths[pi].epoch = sbdEpoch
		
		// s.pathsLock.RUnlock()
	}

	computeAccuracy(s)	

}

func (sbd *Sbd) mergeObservations2(s *session) {
	
	var groupWin string
	mgroups := make(map[string]int)
	max := 0

	// Count the number of times a group has been classified
	for i, _ := range mgroupsObservation {

		groupString := arrayToString(mgroupsObservation[i])
		mgroups[groupString]++
	}

	//Choose the group that appears most
	for gstr, i := range mgroups {
		if i > max {
			max = i
			groupWin = gstr
		}
	}

	groupWinArray, _ := stringToArray(groupWin)

	for i, group := range groupWinArray {
		if group != 0 {
			pi := protocol.PathID(i)
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
		// s.pathsLock.RLock()
		for pi, _ := range s.paths {
			if pi == 0 {
				continue
			}
			mgroup[pi] = 0
		}
		// s.pathsLock.RUnlock()

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
	var state bool
	
	for {

		params := <-sbdChanStruct
		//every T_INTERVAL compute path statistics sbd
		if s.timeIntervalSBD > SBD_T_INTERVAL {
			
			state = true

			s.timeIntervalSBD = 0
			s.numberInterval += 1		
		}


		if (state) {

			state = false

			params.p.pstats.ComputeStatistics(s.numberInterval)
			// p.pstats.PrintFile(p.pathID)

			if s.numberInterval >= 2*SBD_M { // >= N	

				groupChan <- true

			}

		}

		//SBD - compute statistics base	
		params.p.pstats.ComputeStatisticsBase(params.owd, s.numberInterval)
		// we just want to iterate once, but sometimes can iterate twice or more
		for _, losses := range params.lossCount {
			tmpPth := s.paths[losses.pathID]
			tmpPth.pstats.ComputePacketLoss(uint64(losses.lossCount))
		}
		
		// p.pstats.PrintFileOWD(p.pathID, tempo, timeDelay, owd, mgroupsObservation[sbdId])
	}

}
