graph [
  directed 1
  Index 4
  U 0.21271613711724058
  T "17179869184"
  W 3654435409.0
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
    C 619031407.0
    type "dedup"
  ]
  node [
    id 4
    label "5"
    C 619031407.0
    type "dedup"
  ]
  edge [
    source 0
    target 2
    label "322"
  ]
  edge [
    source 0
    target 1
    label "322"
  ]
  edge [
    source 0
    target 3
    label "322"
  ]
  edge [
    source 1
    target 4
    label "265"
  ]
  edge [
    source 2
    target 4
    label "141"
  ]
  edge [
    source 3
    target 4
    label "48"
  ]
]
