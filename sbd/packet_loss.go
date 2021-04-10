package sbd


type Losses struct {
    losses uint64
    everyPacket  uint64
}
type PacketLoss struct {
    packetLoss  float64
    pktLossMT   [M]uint64
    allPktMT    [M]uint64
    // n           uint64
    posInsert   uint64
    Losses
}

func (pl * PacketLoss) initialize() {

    pl.losses = 0
    pl.everyPacket  = 0
}

func (pl * PacketLoss) SetMean(packetLoss float64) { pl.packetLoss = packetLoss}

func (pl * PacketLoss) GetPacketLoss() float64 { return pl.packetLoss }

func (pl * PacketLoss) addLosses(lossCount uint64) { pl.losses += lossCount }

func (pl * PacketLoss) addPacket() { pl.everyPacket++ }

func (pl * PacketLoss) addPacketBase() {

    pl.pktLossMT[pl.posInsert % M] = pl.losses
    pl.allPktMT[pl.posInsert % M]  = pl.everyPacket
    pl.posInsert++

}

func (pl * PacketLoss) sum() (uint64, uint64) {

  var sumPktLoss   uint64
  var sumAllPacket uint64

	// if pl.n < M {
	// 	pl.n++
	// }

  var i uint64
  for i = 0; i < M; i++ {
    sumPktLoss   += pl.pktLossMT[i]
    sumAllPacket += pl.allPktMT[i]
  }

  return sumPktLoss, sumAllPacket
}

func (pl * PacketLoss) computePacketLoss() {
  
    pl.addPacketBase()
    sumPktLoss, sumAllPacket := pl.sum()
    pl.packetLoss = float64(sumPktLoss)/float64(sumAllPacket)
    pl.initialize()
}
