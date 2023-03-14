package quic

import (
	// "fmt"
	"time"
)

type TimeStamp struct {
	ts0 uint64
	ackDelayExponent uint8
}


func (ts * TimeStamp) Setup() {
	ts.ts0 = uint64(time.Now().UnixNano())
	ts.ackDelayExponent = 3
}

func (ts * TimeStamp) TimeStamp() uint64 {
	return uint64(time.Now().UnixNano()) / uint64(time.Microsecond)
}

func (ts * TimeStamp) DecodeADE(ets uint64) uint64 {
	return uint64(ets * 1 << ts.ackDelayExponent)
}

func (ts * TimeStamp) EncodeADE(timestamp uint64) uint64 {
	return uint64(timestamp / (1 << ts.ackDelayExponent))
}