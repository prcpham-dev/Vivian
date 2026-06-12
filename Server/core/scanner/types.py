from typing import List, Literal, TypedDict, Dict, Any

NodeLabel = Literal["File", "Folder", "Class", "Function", "Interface", "Struct", "Enum", "Record"]
RelationshipType = Literal["CONTAINS", "IMPORTS", "CALLS", "INHERITS"]

class GraphNode(TypedDict):
    id: str
    label: NodeLabel
    properties: Dict[str, Any]

class GraphRelationship(TypedDict):
    id: str
    type: RelationshipType
    sourceId: str
    targetId: str
    confidence: float
    reason: str

class KnowledgeGraph(TypedDict):
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    timestamp: int

# Parsed structures internal to file_parser
class FunctionDef(TypedDict, total=False):
    name: str
    params: str
    returnType: str
    line: int
    calledBy: List[str]
    calls: List[str]

class ClassDef(TypedDict, total=False):
    name: str
    extends: List[str]
    line: int

class InterfaceDef(TypedDict, total=False):
    name: str
    extends: List[str]
    line: int

class ParsedFile(TypedDict):
    functions: List[FunctionDef]
    classes: List[ClassDef]
    interfaces: List[InterfaceDef]
    imports: List[str]
