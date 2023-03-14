package sbd

import (
    "math"
    // "fmt"
)

type VarBase struct {
    varBaseT    float64
    numT        uint64
}

type VarEst struct {
    varEst      float64
    varBaseMT   [M]float64
    numMT       [M]uint64
    insPos      uint64
    VarBase
}

func (ve * VarEst) initialize() {
    ve.varBaseT = 0
    ve.numT     = 0
}

func (ve * VarEst) SetMean(meanVarEst float64) { ve.varEst = meanVarEst }

func (ve * VarEst) GetVarEst() float64 { return ve.varEst }
func (ve * VarEst) GetVarBaseT() float64 { return ve.varBaseT }

func (ve * VarEst) addVarBase() {

    ve.varBaseMT[ve.insPos % M] = ve.varBaseT
    ve.numMT[ve.insPos % M]     = ve.numT
    ve.insPos++
}

func (ve * VarEst) sum() (float64, uint64) {

    var sumMT float64
    var numMT uint64

    var i uint64
  	for i = 0; i < M; i++ {
          sumMT += ve.varBaseMT[i]
          numMT += ve.numMT[i]
    }

    return sumMT, numMT
}

func (ve * VarEst) computeVarBase(owd float64, meanOwd MeanOWD){

    ve.varBaseT += float64(math.Abs(float64(owd - meanOwd.mean)))
    ve.numT++
}

func (ve * VarEst) computeVarEst() {
    ve.addVarBase()
    sumMT, numMT := ve.sum()
    ve.varEst = sumMT/float64(numMT)
    ve.initialize()    
}
