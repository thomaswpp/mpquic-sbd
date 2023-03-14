package sbd

// import "fmt"

type SkewBase struct {
    skewBaseT int64
    numT      uint64
}

type SkewEst struct {
    skewEst     float64
    skewBaseMT  [M]int64
    numMT       [M]uint64
    insPos      uint64
    SkewBase
}

func (se * SkewEst) initialize() {
    se.skewBaseT = 0
    se.numT      = 0
}

func (se * SkewEst) SetMean(skewEst float64) { se.skewEst = skewEst}

func (se * SkewEst) GetSkewEst() float64 { return se.skewEst }

func (se * SkewEst) GetSkewBaseT() int64 { return se.skewBaseT }

func (se * SkewEst) addSkewBase() {

    se.skewBaseMT[se.insPos % M] = se.skewBaseT
    se.numMT[se.insPos % M] = se.numT
    se.insPos++
}

func (se * SkewEst) sum() (int64, uint64) {

    var sumMT int64
    var numMT uint64

    var i uint64
	for i = 0; i < M; i++ {
        sumMT += se.skewBaseMT[i]
        numMT += se.numMT[i]
    }

    return sumMT, numMT
}

func (se * SkewEst) computeSkewBaseT(owd float64, meanDelay MeanDelay){

    if owd < meanDelay.mean_delay {
        se.skewBaseT++
    } else if owd > meanDelay.mean_delay {
        se.skewBaseT--
    }

    se.numT++
}

func (se * SkewEst) computeSkewEst() {
    se.addSkewBase()
    sumMT, numMT := se.sum()
    se.skewEst    = float64(sumMT)/float64(numMT)
    se.initialize()
}
