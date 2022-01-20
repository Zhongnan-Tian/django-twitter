from django.core import serializers
from utils.json_encoder import JSONEncoder


class DjangoModelSerializer:

    @classmethod
    def serialize(cls, instance):
        # Django serializers needs QuerySet or list to do the serialization.
        # Wrap instance with [] so it becomes a list.
        return serializers.serialize('json', [instance], cls=JSONEncoder)

    @classmethod
    def deserialize(cls, serialized_data):
        # Note `.object` is to get ORM object. Otherwise, it is a DeserializedObject.
        return list(serializers.deserialize('json', serialized_data))[0].object
