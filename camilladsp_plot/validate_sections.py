#from jsonschema import validate                                         
import json                                                             
import yaml                                                             

from jsonschema import Draft7Validator, validators
import os
import sys

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

    # Replace the $samplerate$ and $channels$ tokens with the corresponding values
    def replace_tokens(self, conf):
        srate = conf['devices']['samplerate']
        channels = conf['devices']['capture']['channels']

        for _filt, fconf in conf['filters'].items():
            if fconf['type'] == 'Conv':
                if 'parameters' in fconf:
                    if "filename" in fconf['parameters']:
                        fconf['parameters']["filename"] = fconf['parameters']["filename"].replace("$samplerate$", str(srate))
                        fconf['parameters']["filename"] = fconf['parameters']["filename"].replace("$channels$", str(channels))

        for step in conf['pipeline']:
            if step['type'] == 'Mixer':
                step['name'] = step['name'].replace("$samplerate$", str(srate))
                step['name'] = step['name'].replace("$channels$", str(channels))
            elif step['type'] == 'Filter':
                for _i, name in enumerate(step['names']):
                    name = name.replace("$samplerate$", str(srate))
                    name = name.replace("$channels$", str(channels))

    def make_paths_absolute(self, conf, configfile_name):
        config_dir = os.path.dirname(os.path.abspath(configfile_name))
        for _name, filt in conf["filters"].items():
            if filt["type"] == "Conv" and filt["parameters"]["type"] == "File":
                filt["parameters"]["filename"] = self.check_and_replace_relative_path(filt["parameters"]["filename"], config_dir)

    def check_and_replace_relative_path(self, path_str, config_dir):
        if not os.path.isabs(path_str):
            in_config_dir = os.path.join(config_dir, path_str)
            if os.path.exists(in_config_dir):
                # File found relative to config file
                return in_config_dir
        # No change, just return it again
        return path_str


    def validate_file(self, file):
        self.errorlist = []
        with open(file) as f:
            conf = yaml.safe_load(f)
        self.validate_with_schemas(conf)
        self.make_paths_absolute(conf, file)
        self.replace_tokens(conf)

        self.validate_devices(conf)
        self.validate_mixers(conf)
        self.validate_filters(conf)
        self.validate_pipeline(conf)
        print("\nErrors:")
        for err in self.errorlist:
            print("/".join([str(p) for p in err[0]]), " : ",  err[1])

    def validate_with_schemas(self, conf):
        # Overall structure
        self.validate(conf, self.section_schema)
        #print(yaml.dump(conf, sort_keys=True))

        # Devices section
        self.validate(conf["devices"], self.devices_schema)

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

    # Validate the pipeline
    def validate_pipeline(self, conf):
        num_channels = conf["devices"]["capture"]["channels"]
        for idx, step in enumerate(conf["pipeline"]):
            if step["type"] == "Mixer":
                mixname = step["name"]
                if mixname not in conf["mixers"].keys():
                    msg = f"Use of missing mixer '{mixname}'"
                    path = ["pipeline", idx]
                    self.errorlist.append((path, msg))
                else:
                    chan_in = conf["mixers"][mixname]["channels"]["in"]
                    if chan_in != num_channels:
                        msg = f"Mixer '{mixname}' has wrong number of input channels. Expected {num_channels}, found {chan_in}."
                        path = ["pipeline", idx]
                        self.errorlist.append((path, msg))
                    num_channels = conf["mixers"][mixname]["channels"]["out"]

            if step["type"] == "Filter":
                if step["channel"] >= num_channels:
                    msg = f"Use of non existing channel {step['channel']}"
                    path = ["pipeline", idx]
                    self.errorlist.append((path, msg))
                for subidx, filtname in enumerate(step["names"]):
                    if filtname not in conf["filters"].keys():
                        msg = f"Use of missing filter '{filtname}'"
                        path = ["pipeline", idx, "names", subidx]
                        self.errorlist.append((path, msg))

        num_channels_out = conf["devices"]["playback"]["channels"]
        if num_channels != num_channels_out:
            msg = f"Pipeline outputs {num_channels} channels, playback device has {num_channels_out}."
            path = ["pipeline"]
            self.errorlist.append((path, msg))


    def validate_mixers(self, conf):
        for mixname, mixer_config in conf["mixers"].items():
            chan_in = mixer_config["channels"]["in"]
            chan_out = mixer_config["channels"]["out"]
            for idx, mapping in enumerate(mixer_config["mapping"]):
                if mapping["dest"] >= chan_out:
                    msg = f"Invalid destination channel {mapping['dest']}, max is {chan_out-1}."
                    path = ["mixers", mixname, "mapping", idx, "dest"]
                    self.errorlist.append((path, msg))
                for subidx, source in enumerate(mapping["sources"]):
                    if source["channel"] >= chan_in:
                        msg = f"Invalid source channel {source['channel']}, max is {chan_in-1}."
                        path = ["mixers", mixname, "mapping", idx, "sources", subidx]
                        self.errorlist.append((path, msg))

    def validate_filters(self, conf):
        maxfreq = conf["devices"]["samplerate"] / 2.0
        for filter_name, filter_conf in conf["filters"].items():
            # Check that frequencies are below Nyquist
            if filter_conf["type"] in ["Biquad", "BiquadCombo"]:
                for freq_prop in ["freq", "freq_act", "freq_target"]:
                    if freq_prop in filter_conf["parameters"].keys():
                        if filter_conf["parameters"][freq_prop] >= maxfreq:
                            msg = "Frequency must be < samplerate/2"
                            path = ["filters", filter_name, "parameters", freq_prop]
                            self.errorlist.append((path, msg))
            # Check that free biquads are stable
            if filter_conf["type"] == "Biquad" and  filter_conf["parameters"]["type"] == "Free":
                a1 = filter_conf["parameters"]["a1"]
                a2 = filter_conf["parameters"]["a2"]
                stable = abs(a2) < 1.0 and abs(a1) < (a2 + 1.0)
                if not stable:
                    msg = "Filter is unstable"
                    path = ["filters", filter_name, "parameters"]
                    self.errorlist.append((path, msg))
            # Check that coefficients files are available
            if filter_conf["type"] == "Conv":
                if filter_conf["parameters"]["type"] == "File":
                    fname = filter_conf["parameters"]["filename"]
                    if not os.path.exists(fname):
                        msg = f"Unable to find coefficent file '{fname}'"
                        path = ["filters", filter_name, "parameters", "filename"]
                        self.errorlist.append((path, msg))

    def validate_devices(self, conf):
        if conf["devices"]["target_level"] >= 2 * conf["devices"]["chunksize"]:
            self.errorlist.append((["devices","target_level"], f"target_level can't be larger than {2 * conf['devices']['chunksize']}"))



if __name__ == "__main__":
    file_validator = CamillaValidator()
    file_validator.validate_file(sys.argv[1])






