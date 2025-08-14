graph [
  directed 1
  Index 4
  U 0.4656006396980956
  T "8589934592"
  W 3999479041.0
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
    C 791553223.0
    type "fft"
  ]
  node [
    id 2
    label "3"
    rank 1
    C 791553223.0
    type "fft"
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
    C 619031407.0
    type "dedup"
  ]
  edge [
    source 0
    target 1
    label "494"
  ]
  edge [
    source 0
    target 2
    label "494"
  ]
  edge [
    source 0
    target 3
    label "494"
  ]
  edge [
    source 0
    target 4
    label "494"
  ]
  edge [
    source 1
    target 4
    label "491"
  ]
  edge [
    source 2
    target 4
    label "503"
  ]
  edge [
    source 3
    target 4
    label "126"
  ]
]
