graph [
  directed 1
  Index 0
  U 0.7505955149536021
  T "17179869184"
  W 12895132757.0
  node [
    id 0
    label "1"
    rank 0
    C 3828182708.9999995
    type "canneal"
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
    C 3828182708.9999995
    type "canneal"
  ]
  node [
    id 4
    label "5"
    C 3828182708.9999995
    type "canneal"
  ]
  edge [
    source 0
    target 2
    label "1112"
  ]
  edge [
    source 0
    target 3
    label "1112"
  ]
  edge [
    source 0
    target 1
    label "1112"
  ]
  edge [
    source 1
    target 4
    label "242"
  ]
  edge [
    source 2
    target 4
    label "208"
  ]
  edge [
    source 3
    target 4
    label "744"
  ]
]
