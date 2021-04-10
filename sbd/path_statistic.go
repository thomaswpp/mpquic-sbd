package sbd


import (
  // "bufio"
  "encoding/csv"
  "os"
  // "io"
  // "sbd"
  // "fmt"
  "strconv"
  "time"
  // "math"
  "github.com/lucas-clemente/quic-go/internal/protocol"
)


const (
    N                           uint64  = 50
    M                           uint64  = 50
    PV                          float64 = 0.7  // p_v
    // PV                          float64 = 0.8  // p_v
)

var (

    timeRelative float64
)
var (
  newFile = [10]bool{true, true, true, true, true, true, true, true, true, true}
)

var (
  newFileOWD = [10]bool{true, true, true, true, true, true, true, true, true, true}
)

var (
  nameFileOWD = [10]string{"", "", "", "", "", "", "", "", "", ""}
)


type PathStats struct {
    Skewness     SkewEst
    Variance     VarEst
    Freq         FreqEst
    Loss         PacketLoss
    MeanOwd      MeanOWD
    MeanDelay    MeanDelay
    PB           bool
}

// newPathStats gets a new path statistics
func NewPathStats(skewness SkewEst, variance VarEst, loss PacketLoss, freq FreqEst, meanOwd MeanOWD, meanDelay MeanDelay) *PathStats {
	return &PathStats{
    Skewness:     skewness,
    Variance:     variance,
    Freq:         freq,
    Loss:         loss,
    MeanOwd:      meanOwd,
    MeanDelay:    meanDelay,
    PB:           false,
	}
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

func (pstats * PathStats) PrintFile(pathid protocol.PathID) {

      if(pathid == 0) {
        return
      }

      name_file := "dados/stats" + strconv.Itoa(int(pathid)) + ".csv"

      if newFile[pathid] {
            newFile[pathid] = false
            
            row := []string{
                  "MeanDelay", 
                  "Skewness", 
                  "Variance",
                  "FreqEst",
                  "Loss",
                  "MeanOwd",
                  "ThreshouldUP",
                  "ThreshouldDown",
            }
            writeCsv(name_file, row)
      }

      d    := pstats.Variance.GetVarEst()*PV
      md   := pstats.MeanDelay.GetMeanDelay()
      mowd := pstats.MeanOwd.GetMeanOwd()


      row := []string{
            strconv.FormatFloat(pstats.MeanDelay.GetMeanDelay(), 'f', -1, 64),
            strconv.FormatFloat(pstats.Skewness.GetSkewEst(), 'f', -1, 64),
            strconv.FormatFloat(pstats.Variance.GetVarEst(), 'f', -1, 64),
            strconv.FormatFloat(pstats.Freq.GetFreqEst(),'f', -1, 64),
            strconv.FormatFloat(pstats.Loss.GetPacketLoss(), 'f', -1, 64),
            strconv.FormatFloat(mowd, 'f', -1, 64),
            strconv.FormatFloat(md+d, 'f', -1, 64),
            strconv.FormatFloat(md-d, 'f', -1, 64),
        }
        writeCsv(name_file, row)
}

// Efficient Read and Write CSV
// https://stackoverflow.com/questions/32027590/efficient-read-and-write-csv-in-go

func (pstats * PathStats) PrintFileOWD(pathid protocol.PathID, tempo time.Time, timeDelay float64, owd float64, m map[protocol.PathID]uint8) {


      if(pathid == 0) {
          return
      }


      if newFileOWD[pathid] {
            newFileOWD[pathid] = false

            t := time.Now()
            nameFileOWD[pathid] = "dados/data" + strconv.Itoa(int(pathid)) + "_" + t.Format("2006-01-02.15:04:05") + ".csv"
            
            row := []string{
                  // "Time", 
                  // "Secs",
                  // "TimeRelative",
                  // "TimeDelay",
                  "OWD", 
                  "MeanOwd",
                  "MeanDelay",
                  "Skewness",
                  "Variance",
                  "FreqEst",
                  "Loss",
                  "SkewBase", 
                  "VarBase",
                  "group",
            }
            writeCsv(nameFileOWD[pathid], row)
      }

      // owdms := float64(owd)/float64(time.Millisecond)
      // secs := float64(tempo.UnixNano())/(1000000000.0)
      // timeRelative = float64(tempo.UnixNano())/(1000000000.0)

      mowd := pstats.MeanOwd.GetMeanOwd() 
      row := []string{
            // tempo.String(),            
            // strconv.FormatFloat(secs, 'f', -1, 64),
            // strconv.FormatFloat(timeDelay, 'f', -1, 64),
            strconv.FormatFloat(owd, 'f', -1, 64),
            strconv.FormatFloat(mowd, 'f', -1, 64),
            strconv.FormatFloat(pstats.MeanDelay.GetMeanDelay(), 'f', -1, 64),
            strconv.FormatFloat(pstats.Skewness.GetSkewEst(), 'f', -1, 64),
            strconv.FormatFloat(pstats.Variance.GetVarEst(), 'f', -1, 64),
            strconv.FormatFloat(pstats.Freq.GetFreqEst(),'f', -1, 64),
            strconv.FormatFloat(pstats.Loss.GetPacketLoss(), 'f', -1, 64),
            strconv.FormatInt(pstats.Skewness.GetSkewBaseT(), 10),
            strconv.FormatFloat(pstats.Variance.GetVarBaseT(), 'f', -1, 64),
            strconv.Itoa(int(m[pathid])),
      }
      writeCsv(nameFileOWD[pathid], row)
}

func (pstats * PathStats) ComputeStatisticsBase(relativeOwd float64, firstTInterval uint64) {
      
      pstats.MeanOwd.add(relativeOwd)

      //compute statistics after first T interval
      if firstTInterval > 0  {
        pstats.Skewness.computeSkewBaseT(relativeOwd, pstats.MeanDelay)
        pstats.Variance.computeVarBase(relativeOwd, pstats.MeanOwd)
      }

}

func (pstats * PathStats) ComputePacketLoss(lossCount uint64) {
      pstats.Loss.addPacket()

      pstats.Loss.addLosses(lossCount)
}

func (pstats * PathStats) ComputeStatistics(firstTInterval uint64) {

      pstats.MeanOwd.computeMeanOwd()
      pstats.MeanDelay.computeMeanDelay(pstats.MeanOwd)

      //compute statistics after first T interval
      if firstTInterval > 0  {
        pstats.Skewness.computeSkewEst()
        pstats.Variance.computeVarEst()
        pstats.Freq.computeFreqEst(pstats.MeanOwd, pstats.MeanDelay, pstats.Variance)
      }
     
      // fmt.Println(pstats.MeanDelay.GetMeanDelay())
        
      pstats.Loss.computePacketLoss()
}
