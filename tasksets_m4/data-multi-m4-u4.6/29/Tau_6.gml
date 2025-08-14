graph [
  directed 1
  Index 6
  U 0.19352161235292442
  T "34359738368"
  W 6649351969.0
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
    C 619031407.0
    type "dedup"
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
    C 619031407.0
    type "dedup"
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
    label "56"
  ]
  edge [
    source 0
    target 2
    label "56"
  ]
  edge [
    source 0
    target 3
    label "56"
  ]
  edge [
    source 0
    target 4
    label "56"
  ]
  edge [
    source 1
    target 4
    label "36"
  ]
  edge [
    source 2
    target 4
    label "442"
  ]
  edge [
    source 3
    target 4
    label "228"
  ]
]
