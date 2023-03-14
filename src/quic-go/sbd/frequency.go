package sbd

// import "fmt"

type FreqEst struct {

    freqEst             float64
    numberOfCrossMT     [M]uint64
    lastStateCross      uint64 //0 - neutro, 1 - up, 2 - down
    lnc                 uint64
    insPos              uint64
    n                   uint64
}

func (fe * FreqEst) SetMean(freqEst float64) { fe.freqEst = freqEst }

func (fe * FreqEst) GetFreqEst() float64 { return fe.freqEst }

func (fe * FreqEst) sum() (uint64) {

  var sumMT uint64

	if fe.n < M {
		fe.n++
	}

  var i uint64
	for i = 0; i < fe.n; i++ {
        sumMT += fe.numberOfCrossMT[i]
  }

  return sumMT
}

func (fe * FreqEst) countCrossOcillation(meanOWD MeanOWD, meanDelay MeanDelay, ve VarEst){

    var numberOfCross uint64

    d   := ve.varEst*PV
    md  := meanDelay.mean_delay

    if ((fe.insPos - fe.lnc) == M) {
        fe.lastStateCross = 0
    }

    if ((meanOWD.mean >= (md + d)) && fe.lastStateCross != 1) {
        numberOfCross = 1
        fe.lastStateCross = 1
        fe.lnc = fe.insPos
    } else if ((meanOWD.mean <= (md - d)) && fe.lastStateCross != 2) {
        numberOfCross = 1
        fe.lastStateCross = 2
        fe.lnc = fe.insPos
    }


    fe.numberOfCrossMT[fe.insPos % M] = numberOfCross
    fe.insPos++
}

func (fe * FreqEst) countCross(meanOWD MeanOWD, meanDelay MeanDelay, ve VarEst){
    var numberOfCross uint64

    d   := ve.varEst*PV
    md  := meanDelay.mean_delay

    if meanOWD.mean >= (md + d) || meanOWD.mean <= (md - d) {
        numberOfCross = 1
    }

    fe.numberOfCrossMT[fe.insPos % M] = numberOfCross
    fe.insPos++
}

func (fe * FreqEst) computeFreqEst(meanOwd MeanOWD, meanDelay MeanDelay, ve VarEst) {
    fe.countCrossOcillation(meanOwd, meanDelay, ve)
    sumMT := fe.sum()
    fe.freqEst = float64(sumMT) / float64(fe.n)
}
