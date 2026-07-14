from app.discovery.models.scientific_object import ScientificObject

from app.modeling.models.scientific_construct import (
    ScientificConstruct,
)

from app.modeling.models.scientific_relationship import (
    ScientificRelationship,
    RelationshipType,
)

from app.modeling.models.scientific_model import (
    ScientificModel,
)

from app.modeling.models.scientific_theory import (
    ScientificTheory,
)


obj = ScientificObject(
    object_id="OBJ-0001",
    name="Orientation Preference",
    description="Consistent preference.",
    phenomena=(),
)

construct = ScientificConstruct(
    construct_id="CON-0001",
    name="Orientation Flexibility",
    definition="Ability to adapt orientation.",
    supporting_objects=(obj,),
)

relationship = ScientificRelationship(
    relationship_id="REL-0001",
    source_construct=construct,
    target_construct=construct,
    relationship_type=RelationshipType.ASSOCIATIVE,
    description="Self relationship.",
)

model = ScientificModel(
    model_id="MOD-0001",
    name="Orientation Model",
    description="Scientific orientation model.",
    constructs=(construct,),
    relationships=(relationship,),
)

theory = ScientificTheory(
    theory_id="THY-0001",
    name="Orientation Theory",
    explanation="General scientific explanation of orientation.",
    models=(model,),
    scope="Human orientation.",
)

print(theory)