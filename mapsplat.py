import argparse
import jinja2
import yaml
import sys
from pathlib import Path
from pprint import pprint
from os import makedirs
from os.path import relpath, dirname
import pycountry
from operator import itemgetter
from shutil import rmtree

START_PEOPLE_STRING = "[//]: # (START_PEOPLE_LIST_DNR)"
END_PEOPLE_STRING = "[//]: # (END_PEOPLE_LIST_DNR)"


INSTITUTION_NAME = """
{% if institution.longname -%}
    {{ institution.longname }} ({{ institution.name }})
{%- else -%}
    {{ institution.name }}
{%- endif %}
""".strip()


INDEX_TEMPLATE = jinja2.Template("""
[//]: # (WARNING: Automatically generated. Do not modify.)
[//]: # (Instead modify mapsplat or the map data and re-generate.)

{% for country_info in tree %}
 * {{ country_info.name }}
{% for institution in country_info.institutions %}
   * [""" + INSTITUTION_NAME + """]({{ by_institution_path }}/{{ institution.name|lower }}) [{{ institution.people|length }}]
{% endfor %}
{% endfor %}
""", trim_blocks=True, lstrip_blocks=True)


INSTITUTION_PAGE = jinja2.Template("""
+++
+++
[//]: # (WARNING: Automatically generated. Do not modify.)
[//]: # (Instead modify mapsplat or the map data and re-generate.)

# """ + INSTITUTION_NAME + """ RSEs
{% for person in institution.people %}
 * {{ person.name }}
{% if person.institutional_page %}
   * Institutional page: [{{ person.institutional_page }}]({{ person.institutional_page }})
{% endif %}
{%- if person.homepage %}
   * Homepage: [{{ person.homepage }}]({{ person.homepage }})
{% endif %}
{%- if person.twitter %}
   * Twitter: [@{{ person.twitter }}](https://twitter.com/{{ person.twitter }})
{% endif %}
{%- if person.github %}
   * GitHub: [{{ person.github }}](https://github.com/{{ person.github }})
{% endif %}
{%- if person.gitlab %}
   * GitLab: [{{ person.gitlab }}](https://gitlab.com/{{ person.gitlab }})
{% endif %}
{%- if person.skills %}
   * Skills: {{ person.skills|join(", ") }}
{% endif %}
{% endfor %}
""", trim_blocks=True, lstrip_blocks=True)


def iso2_to_country_name(country_iso2):
    return pycountry.countries.get(alpha_2=country_iso2).name


def mapsplat(input, output, insert_index):
    with open(input) as f:
        map_data = yaml.safe_load(f)
    data_tree = {}
    by_place = {}
    for place in map_data["places"]:
        if not place["country"]:
            print(f"Warning: skipping institution {place['name']} because it is missing a country")
            continue
        by_place[place["name"]] = data_tree\
            .setdefault(
                place["country"],
                {
                    "name": iso2_to_country_name(place["country"]),
                    "institutions": {}
                }
            )["institutions"]\
            .setdefault(place["name"], place)
    for person in map_data["persons"]:
        if person["place"] not in by_place:
            print(f"Warning: skipping person {person['name']} because could not find institution {person['place']}")
            continue
        if "name" not in person:
            print(f"Warning: skipping nameless person")
            continue
        by_place[person["place"]].setdefault("people", []).append(person)
    data_tree = sorted((
        {
            "iso2": country_iso2,
            "name": country_info["name"],
            "institutions": sorted((
                {
                    "short": institution_short,
                    **institution_info,
                    "people": sorted(institution_info["people"], key=itemgetter("name"))
                }
                for institution_short, institution_info in country_info["institutions"].items()
                if institution_info.get("people")
            ), key=itemgetter("short"))
        }
        for country_iso2, country_info in data_tree.items() 
    ), key=itemgetter("name"))
    rmtree(output)
    makedirs(output, exist_ok=True)

    up_one = insert_index is not None and insert_index != "_index.md"
    by_institution_path = ("../" if up_one else "") + relpath(output, dirname(insert_index))
    index_text = INDEX_TEMPLATE.render({
        "tree": data_tree,
        "by_institution_path": by_institution_path,
    })
    if insert_index:
        with open(insert_index, "r+") as index_f:
            lines = index_f.read().splitlines(keepends=True)
            start_line_idx = None
            end_line_idx = None
            for idx, line in enumerate(lines):
                if line.startswith(START_PEOPLE_STRING):
                    start_line_idx = idx
                elif start_line_idx is not None and line.startswith(END_PEOPLE_STRING):
                    end_line_idx = idx
            if start_line_idx is not None and end_line_idx is not None:
                lines = [*lines[:start_line_idx + 1], index_text, "\n", *lines[end_line_idx:]]
            else:
                print("Could not find place to insert people list", file=sys.stderr)
                sys.exit(-1)
            index_f.seek(0)
            index_f.write("".join(lines))
            index_f.truncate()
        with open(output / "_index.md", "w") as index_f:
            index_f.write("+++\n+++")
    else:
        with open(output / "_index.md", "w") as index_f:
            index_f.write(index_text)
    for place_info in by_place.values():
        with open(output / (place_info["name"].lower() + ".md"), "w") as place_f:
            place_f.write(INSTITUTION_PAGE.render({
                "institution": place_info
            }))


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help="input yaml", type=Path)
    parser.add_argument('output', help="output directory", type=Path)
    parser.add_argument('--insert-index', help="insert index into this file", type=Path)
    args = parser.parse_args(argv)
    mapsplat(args.input, args.output, args.insert_index)


if __name__ == "__main__":
    main()