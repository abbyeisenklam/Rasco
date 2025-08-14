graph [
  directed 1
  Index 2
  U 1.180235116975382
  T "8589934592"
  W 10138142458.0
  node [
    id 0
    label "1"
    rank 0
    C 791553223.0
    type "fft"
  ]
  node [
    id 1
    label "2"
    rank 1
    C 3828182708.9999995
    type "canneal"
  ]
  node [
    id 2
    label "3"
    rank 1
    C 3828182708.9999995
    type "canneal"
  ]
  node [
    id 3
    label "4"
    rank 1
    C 898670594.0
    type "streamcluster"
  ]
  node [
    id 4
    label "5"
    C 791553223.0
    type "fft"
  ]
  edge [
    source 0
    target 3
    label "213"
  ]
  edge [
    source 0
    target 1
    label "213"
  ]
  edge [
    source 0
    target 2
    label "213"
  ]
  edge [
    source 1
    target 4
    label "375"
  ]
  edge [
    source 2
    target 4
    label "55"
  ]
  edge [
    source 3
    target 4
    label "274"
  ]
]
