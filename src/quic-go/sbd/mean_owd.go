package sbd

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
