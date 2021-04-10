package sbd

// import (
// 	"time"
// )

//conversão de tipos time.Duration
//https://stackoverflow.com/questions/41503758/conversion-of-time-duration-type-microseconds-value-to-milliseconds

type MeanOWD struct {
	mean float64
	n uint64
  	sumT float64
}

func (meanOWD *MeanOWD) initialize() {

	meanOWD.sumT = 0
	meanOWD.n = 0

}

func (meanOwd *MeanOWD) GetMeanOwd() float64 { return meanOwd.mean }

func (meanOwd *MeanOWD) add(owd float64) {
	meanOwd.n++
	meanOwd.sumT += owd
}

func (meanOwd * MeanOWD) computeMeanOwd() {

	meanOwd.mean = meanOwd.sumT / float64(meanOwd.n)
	meanOwd.initialize()
}
