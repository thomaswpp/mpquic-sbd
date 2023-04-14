package sbd


const (
    N                           uint64  = 50
    M                           uint64  = 50
    PV                          float64 = 0.7  // p_v
)

var (

    timeRelative float64
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


func (pstats * PathStats) ComputeStatisticsBase(relativeOwd float64, firstTInterval uint64) {
      
      pstats.MeanOwd.add(relativeOwd)

      //compute statistics after first T interval
      if firstTInterval > 0  {
        pstats.Skewness.computeSkewBaseT(relativeOwd, pstats.MeanDelay)
        pstats.Variance.computeVarBase(relativeOwd, pstats.MeanOwd)
      }

}

func (pstats * PathStats) Restart() {
      
      pstats.MeanOwd.initialize()

      pstats.Skewness.initialize()
      pstats.Variance.initialize()

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
        
      pstats.Loss.computePacketLoss()
}
