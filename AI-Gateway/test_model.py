from app.discovery.models.scientific_object import ScientificObject
from app.modeling.models.scientific_construct import ScientificConstruct
from app.modeling.models.scientific_relationship import (
    ScientificRelationship,
    RelationshipType,
)
from app.modeling.models.scientific_model import ScientificModel

obj1 = ScientificObject(
    object_id="OBJ-0001",
    name="Orientation Preference",
    description="Consistent preference.",
    phenomena=(),
)

obj2 = ScientificObject(
    object_id="OBJ-0002",
    name="Orientation Adaptability",
    description="Adaptive orientation.",
    phenomena=(),
)

construct1 = ScientificConstruct(
    construct_id="CON-0001",
    name="Orientation Flexibility",
    definition="Ability to adapt orientation.",
    supporting_objects=(obj1,),
)

construct2 = ScientificConstruct(
    construct_id="CON-0002",
    name="Orientation Stability",
    definition="Consistency across contexts.",
    supporting_objects=(obj2,),
)

relationship = ScientificRelationship(
    relationship_id="REL-0001",
    source_construct=construct1,
    target_construct=construct2,
    relationship_type=RelationshipType.FUNCTIONAL,
    description="Orientation flexibility contributes to orientation stability.",
)

model = ScientificModel(
    model_id="MOD-0001",
    name="Orientation Adaptation Model",
    description="Scientific model describing the relationship between flexibility and stability.",
    constructs=(
        construct1,
        construct2,
    ),
    relationships=(
        relationship,
    ),
)

print(model)