graph [
  directed 1
  Index 7
  U 0.399513327924069
  T "17179869184"
  W 6863586711.0
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
    target 1
    label "511"
  ]
  edge [
    source 0
    target 2
    label "511"
  ]
  edge [
    source 0
    target 3
    label "511"
  ]
  edge [
    source 1
    target 4
    label "255"
  ]
  edge [
    source 2
    target 4
    label "491"
  ]
  edge [
    source 3
    target 4
    label "606"
  ]
]
