graph [
  directed 1
  Index 4
  U 0.1164001599245239
  T "34359738368"
  W 3999479041.0
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
    C 898670594.0
    type "streamcluster"
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
    C 619031407.0
    type "dedup"
  ]
  edge [
    source 0
    target 3
    label "311"
  ]
  edge [
    source 0
    target 1
    label "311"
  ]
  edge [
    source 0
    target 2
    label "311"
  ]
  edge [
    source 1
    target 4
    label "736"
  ]
  edge [
    source 2
    target 4
    label "1804"
  ]
  edge [
    source 3
    target 4
    label "1588"
  ]
]
