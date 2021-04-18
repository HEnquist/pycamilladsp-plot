from jsonschema import validate                                         
import json                                                             
import yaml                                                             

with open("schemas/sections.json") as f:
    section_schema = json.load(f)

with open("schemas/devices.json") as f:
    devices_schema = json.load(f)

with open("schemas/playback.json") as f:
    playback_schemas = json.load(f)

with open("schemas/capture.json") as f:
    capture_schemas = json.load(f)

with open("schemas/filter.json") as f:
    filter_schema = json.load(f)

with open("schemas/biquads.json") as f:
    biquad_schemas = json.load(f)

with open("schemas/conv.json") as f:
    conv_schemas = json.load(f)

with open("schemas/basicfilters.json") as f:
    basics_schemas = json.load(f)

with open("schemas/pipeline.json") as f:
    pipeline_schemas = json.load(f)

with open("schemas/mixer.json") as f:
    mixer_schema = json.load(f)
with open("schemas/mixermapping.json") as f:
    mixermapping_schema = json.load(f)
with open("schemas/mixersource.json") as f:
    mixersource_schema = json.load(f)

#with open("schemas/devices.json") as f:
#    deviceschema = json.load(f)

with open("../validateme.yml") as f:
    conf = yaml.safe_load(f)


# Overall structure
validate(instance=conf, schema=section_schema)

# Devices section
validate(instance=conf["devices"], schema=devices_schema)

# Playback device
playback_type = conf["devices"]["playback"]["type"]
playback_schema = playback_schemas[playback_type]
validate(instance=conf["devices"]["playback"], schema=playback_schema)

# Capture device
capture_type = conf["devices"]["capture"]["type"]
capture_schema = capture_schemas[capture_type]
validate(instance=conf["devices"]["capture"], schema=capture_schema)

# Filters
if "filters" in conf: 
    for name, filt in conf["filters"].items():
        print(f"Validating filter {name}")
        validate(instance=filt, schema=filter_schema)
        filt_type = filt["type"]
        filt_subtype = filt["parameters"]["type"]
        if filt_type == "Biquad":
            schema = biquad_schemas["Biquad"]
            validate(instance=filt["parameters"], schema=schema)
            schema = biquad_schemas[filt_subtype]
            validate(instance=filt["parameters"], schema=schema)
        elif filt_type == "Conv":
            schema = conv_schemas["Conv"]
            validate(instance=filt["parameters"], schema=schema)
            schema = conv_schemas[filt_subtype]
            validate(instance=filt["parameters"], schema=schema)
        elif filt_type in basics_schemas.keys():
            schema = basics_schemas[filt_type]
            validate(instance=filt["parameters"], schema=schema)

# Mixers
if "mixers" in conf: 
    for name, mix in conf["mixers"].items():
        print(f"Validating mixer {name}")
        validate(instance=mix, schema=mixer_schema)
        for mapping in mix["mapping"]:
            validate(instance=mapping, schema=mixermapping_schema)
            for source in mapping["sources"]:
                validate(instance=source, schema=mixersource_schema)

# Pipeline
if "pipeline" in conf: 
    for step in conf["pipeline"]:
        print(f"Validating pipeline step")
        validate(instance=step, schema=pipeline_schemas["PipelineStep"])
        step_type = step["type"]
        schema = pipeline_schemas[step_type]
        validate(instance=step, schema=schema)








