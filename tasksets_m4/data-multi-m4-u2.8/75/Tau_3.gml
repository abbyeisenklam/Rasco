graph [
  directed 1
  Index 3
  U 0.8066407353617251
  T "8589934592"
  W 6928991156.0
  node [
    id 0
    label "1"
    rank 0
    C 619031407.0
    type "dedup"
  ]
  node [
    id 1
    label "2"
    rank 1
    C 791553223.0
    type "fft"
  ]
  node [
    id 2
    label "3"
    rank 1
    C 898670594.0
    type "streamcluster"
  ]
  node [
    id 3
    label "4"
    rank 1
    C 791553223.0
    type "fft"
  ]
  node [
    id 4
    label "5"
    C 3828182708.9999995
    type "canneal"
  ]
  edge [
    source 0
    target 1
    label "1067"
  ]
  edge [
    source 0
    target 2
    label "1067"
  ]
  edge [
    source 0
    target 3
    label "1067"
  ]
  edge [
    source 1
    target 4
    label "141"
  ]
  edge [
    source 2
    target 4
    label "295"
  ]
  edge [
    source 3
    target 4
    label "251"
  ]
]
