graph [
  directed 1
  Index 3
  U 0.8315809417981654
  T "8589934592"
  W 7143225898.0
  node [
    id 0
    label "1"
    rank 0
    C 898670594.0
    type "streamcluster"
  ]
  node [
    id 1
    label "2"
    rank 1
    C 898670594.0
    type "streamcluster"
  ]
  node [
    id 2
    label "3"
    rank 1
    C 619031407.0
    type "dedup"
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
    C 3828182708.9999995
    type "canneal"
  ]
  edge [
    source 0
    target 1
    label "4668"
  ]
  edge [
    source 0
    target 2
    label "4668"
  ]
  edge [
    source 0
    target 3
    label "4668"
  ]
  edge [
    source 1
    target 4
    label "4700"
  ]
  edge [
    source 2
    target 4
    label "4148"
  ]
  edge [
    source 3
    target 4
    label "2795"
  ]
]
