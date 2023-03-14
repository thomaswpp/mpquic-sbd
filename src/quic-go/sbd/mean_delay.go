package sbd

type MeanDelay struct {
	means [M]float64
	insPos uint64
	mean_delay float64
	n uint64
}

func (meanDelay * MeanDelay) GetMeanDelay() float64 {	return meanDelay.mean_delay	 }

func (meanDelay * MeanDelay) addMeanDelay(meanOwd MeanOWD) {

    meanDelay.means[meanDelay.insPos % M] = meanOwd.mean
    meanDelay.insPos++
}

func (meanDelay * MeanDelay) sum() float64 {

	var sumMT float64

	if meanDelay.n < M {
		meanDelay.n++
	}

	var i uint64
	for i = 0; i < meanDelay.n; i++ {
        sumMT += meanDelay.means[i]
    }

	return sumMT
}

func (meanDelay * MeanDelay) computeMeanDelay(meanOwd MeanOWD){
	meanDelay.addMeanDelay(meanOwd)
    sumMT := meanDelay.sum()
    meanDelay.mean_delay = sumMT/float64(meanDelay.n)
}
