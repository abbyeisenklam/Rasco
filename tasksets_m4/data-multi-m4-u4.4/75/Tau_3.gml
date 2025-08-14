graph [
  directed 1
  Index 3
  U 0.19854265803587623
  T "34359738368"
  W 6821873785.0
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
    C 791553223.0
    type "fft"
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
    target 1
    label "408"
  ]
  edge [
    source 0
    target 2
    label "408"
  ]
  edge [
    source 0
    target 3
    label "408"
  ]
  edge [
    source 1
    target 4
    label "67"
  ]
  edge [
    source 2
    target 4
    label "240"
  ]
  edge [
    source 3
    target 4
    label "312"
  ]
]
