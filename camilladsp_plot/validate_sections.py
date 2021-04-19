#from jsonschema import validate                                         
import json                                                             
import yaml                                                             

from jsonschema import Draft7Validator, validators
import os

# https://python-jsonschema.readthedocs.io/en/latest/faq/#why-doesn-t-my-schema-that-has-a-default-property-actually-set-the-default-on-my-instance
def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(
            validator, properties, instance, schema,
        ):
            yield error

    return validators.extend(
        validator_class, {"properties" : set_defaults},
    )

class CamillaValidator():

    def __init__(self):
        self.validator = extend_with_default(Draft7Validator)
        # Overall
        with open(self.get_full_path("schemas/sections.json")) as f:
            self.section_schema = json.load(f)

        # Devices
        with open(self.get_full_path("schemas/devices.json")) as f:
            self.devices_schema = json.load(f)
        with open(self.get_full_path("schemas/playback.json")) as f:
            self.playback_schemas = json.load(f)
        with open(self.get_full_path("schemas/capture.json")) as f:
            self.capture_schemas = json.load(f)

        # Filters
        with open(self.get_full_path("schemas/filter.json")) as f:
            self.filter_schema = json.load(f)
        with open(self.get_full_path("schemas/biquads.json")) as f:
            self.biquad_schemas = json.load(f)
        with open(self.get_full_path("schemas/biquadcombo.json")) as f:
            self.biquadcombo_schemas = json.load(f)
        with open(self.get_full_path("schemas/conv.json")) as f:
            self.conv_schemas = json.load(f)
        with open(self.get_full_path("schemas/basicfilters.json")) as f:
            self.basics_schemas = json.load(f)

        # Pipeline
        with open(self.get_full_path("schemas/pipeline.json")) as f:
            self.pipeline_schemas = json.load(f)

        # Mixer
        with open(self.get_full_path("schemas/mixer.json")) as f:
            self.mixer_schema = json.load(f)
        with open(self.get_full_path("schemas/mixermapping.json")) as f:
            self.mixermapping_schema = json.load(f)
        with open(self.get_full_path("schemas/mixersource.json")) as f:
            self.mixersource_schema = json.load(f)


    def validate(self, conf, schema):
        try:
            self.validator(schema).validate(conf)
        except Exception as e:
            self.errorlist.append(str(e))

    # DefaultValidatingDraft7Validator(schema).validate(obj)
    def get_full_path(self, file):
        return os.path.join(os.path.dirname(__file__), file)

    def validate_file(self, file):
        self.errorlist = []
        with open("../validateme.yml") as f:
            conf = yaml.safe_load(f)
        self.validate_with_schemas(conf)
        self.validate_devices(conf)
        self.validate_mixers(conf)
        self.validate_filters(conf)
        self.validate_pipeline(conf)

    def validate_with_schemas(self, conf):
        # Overall structure
        print(yaml.dump(conf, sort_keys=True))
        #validate(instance=conf, schema=section_schema)
        self.validate(conf, self.section_schema)
        print(yaml.dump(conf, sort_keys=True))

        # Devices section
        #validate(instance=conf["devices"], schema=devices_schema)
        self.validate(conf["devices"], self.devices_schema)
        print(yaml.dump(conf, sort_keys=True))

        # Playback device
        playback_type = conf["devices"]["playback"]["type"]
        playback_schema = self.playback_schemas[playback_type]
        self.validate(conf["devices"]["playback"], playback_schema)

        # Capture device
        capture_type = conf["devices"]["capture"]["type"]
        capture_schema = self.capture_schemas[capture_type]
        self.validate(conf["devices"]["capture"], capture_schema)

        # Filters
        if "filters" in conf: 
            for name, filt in conf["filters"].items():
                print(f"Validating filter {name}")
                self.validate(filt, self.filter_schema)
                filt_type = filt["type"]
                filt_subtype = filt["parameters"]["type"]
                if filt_type == "Biquad":
                    schema = self.biquad_schemas["Biquad"]
                    self.validate(filt["parameters"], schema)
                    schema = self.biquad_schemas[filt_subtype]
                    self.validate(filt["parameters"], schema)
                elif filt_type == "BiquadCombo":
                    schema = self.biquadcombo_schemas["BiquadCombo"]
                    self.validate(filt["parameters"], schema)
                    schema = self.biquadcombo_schemas[filt_subtype]
                    self.validate(filt["parameters"], schema)
                elif filt_type == "Conv":
                    schema = self.conv_schemas["Conv"]
                    self.validate(filt["parameters"], schema)
                    schema = self.conv_schemas[filt_subtype]
                    self.validate(filt["parameters"], schema)
                elif filt_type in self.basics_schemas.keys():
                    schema = self.basics_schemas[filt_type]
                    self.validate(filt["parameters"], schema)

        # Mixers
        if "mixers" in conf: 
            for name, mix in conf["mixers"].items():
                print(f"Validating mixer {name}")
                self.validate(mix, self.mixer_schema)
                for mapping in mix["mapping"]:
                    self.validate(mapping, self.mixermapping_schema)
                    for source in mapping["sources"]:
                        self.validate(source, self.mixersource_schema)

        # Pipeline
        if "pipeline" in conf: 
            for step in conf["pipeline"]:
                print(f"Validating pipeline step")
                self.validate(step, self.pipeline_schemas["PipelineStep"])
                step_type = step["type"]
                schema = self.pipeline_schemas[step_type]
                self.validate(step, schema)

    def validate_pipeline(self, conf):
        pass

    def validate_mixers(self, conf):
        pass

    def validate_filters(self, conf):
        pass

    def validate_devices(self, conf):
        pass


if __name__ == "__main__":
    file_validator = CamillaValidator()
    file_validator.validate_file("asdad")








