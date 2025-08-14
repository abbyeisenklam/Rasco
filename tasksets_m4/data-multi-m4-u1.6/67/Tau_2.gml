graph [
  directed 1
  Index 2
  U 0.22033021663082764
  T "17179869184"
  W 3785244299.0
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
    C 791553223.0
    type "fft"
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
    C 791553223.0
    type "fft"
  ]
  node [
    id 4
    label "5"
    C 791553223.0
    type "fft"
  ]
  edge [
    source 0
    target 2
    label "31"
  ]
  edge [
    source 0
    target 3
    label "31"
  ]
  edge [
    source 0
    target 1
    label "31"
  ]
  edge [
    source 1
    target 4
    label "49"
  ]
  edge [
    source 2
    target 4
    label "20"
  ]
  edge [
    source 3
    target 4
    label "29"
  ]
]
