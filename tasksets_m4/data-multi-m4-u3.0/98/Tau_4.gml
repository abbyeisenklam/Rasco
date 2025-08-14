graph [
  directed 1
  Index 4
  U 0.8910329139325768
  T "4294967296"
  W 3826957225.0
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
    C 619031407.0
    type "dedup"
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
    target 1
    label "3501"
  ]
  edge [
    source 0
    target 3
    label "3501"
  ]
  edge [
    source 0
    target 2
    label "3501"
  ]
  edge [
    source 1
    target 4
    label "3143"
  ]
  edge [
    source 2
    target 4
    label "15753"
  ]
  edge [
    source 3
    target 4
    label "18147"
  ]
]
