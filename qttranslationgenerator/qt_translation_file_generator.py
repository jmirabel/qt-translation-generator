import xml.etree.ElementTree as elementTree
import time
import re
import tqdm
import json
from googletrans import Translator
import os
from .language_codes import language_dict


class _ParsePythonFormat:
    _regex_any = re.compile("{([^}]*)}")
    _regex_number = re.compile("{([0-9]*)}")

    def __init__(self, input: str):
        self.input = input
        self._mapping = {}
        output = ""
        prev = 0
        for k, match in enumerate(_ParsePythonFormat._regex_any.finditer(input)):
            self._mapping[str(k)] = match[1]
            output += input[prev:match.start(1)]
            output += str(k)
            prev = match.end(1)
        output += input[prev:]

        self.output = output

    def reverse(self, output):
        input = ""
        prev = 0
        for match in _ParsePythonFormat._regex_number.finditer(output):
            input += output[prev:match.start(1)]
            input += self._mapping[match[1]]
            prev = match.end(1)
        input += output[prev:]
        return input

    @property
    def has_format(self):
        return len(self._mapping) > 0


class QtTranslationFileGenerator:
    def __init__(self, src_translation_file_path, dest_lang_code, cache_file = None) -> None:
        """Initializes Qt translation file generator

        Args:
            src_translation_file_path (string): Source translation file path
            dest_lang_code (string): dest_lang_code (string): Destination translation language code
            cache_file (string): path to a JSON file (may not exist) where cache for the destination language is to be stored
        """
        try:
            language_name = language_dict[dest_lang_code]
            print(
                '{0} [{1}] -> Language code is valid.'.format(language_name, dest_lang_code))
        except KeyError:
            print('{0} is not in language code dictionary.'.format(dest_lang_code))
            raise LookupError(
                '{0} is not in language code dictionary.'.format(dest_lang_code))

        self.src_translation_file_path = src_translation_file_path
        self.dest_lang_code = dest_lang_code

        self._cache_file = cache_file

        if self.src_translation_file_path is None:
            raise ValueError("Translation file name is not valid.")

        self._load_cache()

    def _load_cache(self):
        self.translated_text_map = {}
        if self._cache_file is not None and os.path.isfile(self._cache_file):
            with open(self._cache_file, "r") as f:
                translated_text_map = json.load(f)
            # Check that cache file contains what it should contain
            assert isinstance(translated_text_map, dict)
            assert all(isinstance(k, str) for k in translated_text_map.keys())
            assert all(isinstance(v, str) for v in translated_text_map.values())
            self.translated_text_map = translated_text_map
        self._n_consecutive_translate_without_cache_write = 0

    def _write_cache(self):
        if self._cache_file is not None:
            tmp_cache_file = self._cache_file + ".tmp"
            with open(tmp_cache_file, "w") as f:
                json.dump(self.translated_text_map, f)
            os.rename(tmp_cache_file, self._cache_file)
            self._n_consecutive_translate_without_cache_write = 0

    def get_generated_translation_file_path(self):
        # get file path without extension
        src_translation_file_path_no_ext = os.path.splitext(self.src_translation_file_path)[0]
        return '{0}_generated.ts'.format(src_translation_file_path_no_ext)

    def translate(self):
        """Generates new Qt translation file that includes translation texts for language specified in the given dest_lang_code
        """
        with open(self.src_translation_file_path, 'rt', encoding="utf8") as f:
            tree = elementTree.parse(f)

        self.__translate(tree)
        self._write_cache()

    def __translate(self, tree):
        """translate texts from given XML tree

        Args:
            tree (XML document): Translation XML document
        """
        root = tree.getroot()
        google_translator = Translator()

        messages = list(root.iterfind("./context/message"))
        bar = tqdm.tqdm(messages)
        for message_node in bar:
            self.__parse_message_node(google_translator, message_node, bar)

        tree.write(self.get_generated_translation_file_path(), encoding="UTF-8", xml_declaration=True)

    def __parse_message_node(self, google_translator, message_node, bar):
        source_node = message_node.find('source')
        translate_node = message_node.find('translation')

        if translate_node is not None:
            try:
                if "type" in translate_node.attrib:
                    attr_translation_type = translate_node.attrib["type"]
                    if attr_translation_type == 'unfinished' and translate_node.text in ["", None]:
                        source_text = self.replace_special_characters(
                            source_node.text)

                        bar.write('Translating {0} ...'.format(source_text))
                        if source_text in self.translated_text_map:
                            translate_node.text = self.translated_text_map[source_text]
                            bar.write('  Result from cache: {0}'.format(translate_node.text))
                        else:
                            # Handle placeholders
                            placeholder = _ParsePythonFormat(source_text)

                            if placeholder.has_format:
                                bar.write("  Placeholder: {0}".format(placeholder.output))
                            translated_text = google_translator.translate(
                                placeholder.output, src='en', dest=self.dest_lang_code).text
                            translated_text = placeholder.reverse(translated_text)
                            translate_node.text = translated_text
                            self.translated_text_map[source_text] = translated_text
                            bar.write('  Result: {0}'.format(translated_text))

                            if self._n_consecutive_translate_without_cache_write > 10:
                                self._write_cache()
                            time.sleep(1)
                    else:
                        bar.write("Skip already translated: {0}".format(source_node.text))
            except Exception as e:
                print('parse_message_node : Exception during translation of {0}. Exception : {1}'.format(
                    source_node.text, str(e)))
                raise

    def replace_special_characters(self, str_in: str):
        """Replaces escape sequence in XML file with special characters 
        Special Character   Escape Sequence Purpose  
         &                   &amp;           Ampersand sign 
         '                   &apos;          Single quote 
         "                   &quot;          Double quote
         >                   &gt;            Greater than 
         <                   &lt;            Less than

        Args:
            str_in (string): input string to be replaced
        """
        str_out = str_in
        str_out = str_out.replace("&quot;", "\"")
        str_out = str_out.replace("&apos;", "\'")
        str_out = str_out.replace("&lt;",   "<")
        str_out = str_out.replace("&gt;",   ">")
        str_out = str_out.replace("&amp;",  "\&")
        str_out = str_out.replace("&",      "")
        return str_out
