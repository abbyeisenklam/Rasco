graph [
  directed 1
  Index 6
  U 0.5863105187308975
  T "17179869184"
  W 10072738013.0
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
    C 3828182708.9999995
    type "canneal"
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
    C 3828182708.9999995
    type "canneal"
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
    label "3604"
  ]
  edge [
    source 0
    target 3
    label "3604"
  ]
  edge [
    source 0
    target 2
    label "3604"
  ]
  edge [
    source 1
    target 4
    label "3315"
  ]
  edge [
    source 2
    target 4
    label "1706"
  ]
  edge [
    source 3
    target 4
    label "1954"
  ]
]
