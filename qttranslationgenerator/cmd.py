#!/usr/bin/env python3

from qttranslationgenerator import QtTranslationFileGenerator
import sys
import argparse

cache_file_fmt = ".translation_cache_{lang}.json"

def translate_to(src_translation_file, target_lang_code, in_place):
    try:
        qt_translation_file_generator = QtTranslationFileGenerator(
            src_translation_file,
            target_lang_code,
            cache_file=cache_file_fmt.format(lang=target_lang_code),
            in_place=in_place,
        )
        qt_translation_file_generator.translate()
    except Exception as e:
        print("Exception {0}".format(str(e)))
        raise


def translate_to_all_languages(src_translation_file, languages, in_place: bool):
    try:
        for key in languages:
            translate_to(src_translation_file, key, in_place)
    except Exception as e:
        print("Exception {0}".format(str(e)))
        raise


def qt_translation_generator():
    parser = argparse.ArgumentParser(
        description="Use Google Translate to populate a Qt TS file."
    )
    parser.add_argument("ts_file")
    parser.add_argument("languages", nargs="+")
    parser.add_argument("-i", "--in-place", help="Modify the input file. If not passed, the result is saved to file `_generated`.", action="store_true")
    args = parser.parse_args()

    translate_to_all_languages(args.ts_file, args.languages, args.in_place)

if __name__ == "__main__":
    qt_translation_file_generator()
