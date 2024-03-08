import xml.etree.ElementTree as elementTree
import time
import re
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
    def __init__(self, src_translation_file_path, output_dir = '.') -> None:
        """Initializes Qt translation file generator

        Args:
            src_translation_file_path (string): Source translation file path
        """
        self.src_translation_file_path = src_translation_file_path
        self.src_translation_file_name = os.path.basename(
            self.src_translation_file_path)
        # get file name without extension
        self.src_translation_file_name = os.path.splitext(
            self.src_translation_file_name)[0]
        self.output_dir = output_dir
        self.translated_text_map = {}

        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        if self.src_translation_file_name is None:
            raise ValueError("Translation file name is not valid.")

        print(self.src_translation_file_name)

    def get_generated_translation_file_name(self, dest_lang_code):
        return '{0}_generated.ts'.format(self.src_translation_file_name)

    def get_generated_translation_file_path(self, dest_lang_code):
        return '{0}/{1}'.format(self.output_dir, self.get_generated_translation_file_name(dest_lang_code))

    def translate(self, dest_lang_code, cache_file = None):
        """Generates new Qt translation file that includes translation texts for language specified in the given dest_lang_code

        Args:
            dest_lang_code (string): dest_lang_code (string): Destination translation language code
        """
        if cache_file is not None and os.path.isfile(cache_file):
            with open(cache_file, "r") as f:
                translated_text_map = json.load(f)
            # Check that cache file contains what it should contain
            assert isinstance(translated_text_map, dict)
            assert all(isinstance(k, str) for k in translated_text_map.keys())
            assert all(isinstance(v, str) for v in translated_text_map.values())
            self.translated_text_map = translated_text_map
        try:
            language_name = language_dict[dest_lang_code]
            print(
                '{0} [{1}] -> Language code is valid.'.format(language_name, dest_lang_code))
        except KeyError:
            print('{0} is not in language code dictionary.'.format(dest_lang_code))
            raise LookupError(
                '{0} is not in language code dictionary.'.format(dest_lang_code))

        with open(self.src_translation_file_path, 'rt', encoding="utf8") as f:
            tree = elementTree.parse(f)

        self.__translate(tree, dest_lang_code)

        if cache_file is not None:
            tmp_cache_file = cache_file + ".tmp"
            with open(tmp_cache_file, "w") as f:
                json.dump(self.translated_text_map, f)
            os.rename(tmp_cache_file, cache_file)

    def __translate(self, tree, dest_lang_code):
        """translate texts from given XML tree

        Args:
            tree (XML document): Translation XML document
            dest_lang_code (string): destination language code
        """
        root = tree.getroot()
        google_translator = Translator()
        for child_node in root:
            if child_node.tag == 'context':
                self.__parse_translation_context(
                    google_translator, child_node, dest_lang_code)

        tree.write(self.get_generated_translation_file_path(
            dest_lang_code), encoding="UTF-8", xml_declaration=True)

    def __parse_translation_context(self, google_translator, context_node, dest_lang_code):
        for message_node in context_node.iter('message'):
            self.__parse_message_node(
                google_translator, message_node, dest_lang_code)

    def __parse_message_node(self, google_translator, message_node, dest_lang_code):
        source_node = message_node.find('source')
        translate_node = message_node.find('translation')

        if translate_node is not None:
            try:
                if "type" in translate_node.attrib:
                    attr_translation_type = translate_node.attrib["type"]
                    if attr_translation_type == 'unfinished' and translate_node.text in ["", None]:
                        source_text = self.replace_special_characters(
                            source_node.text)

                        print('Translating {0} ...'.format(source_text))
                        if source_text in self.translated_text_map:
                            translate_node.text = self.translated_text_map[source_text]
                            print('  Result from cache: {0}'.format(translate_node.text))
                        else:
                            # Handle placeholders
                            placeholder = _ParsePythonFormat(source_text)

                            if placeholder.has_format:
                                print("  Placeholder: {0}".format(placeholder.output))
                            translated_text = google_translator.translate(
                                placeholder.output, src='en', dest=dest_lang_code).text
                            translated_text = placeholder.reverse(translated_text)
                            translate_node.text = translated_text
                            self.translated_text_map[source_text] = translated_text
                            print('  Result: {0}'.format(translated_text))
                            time.sleep(1)
                    else:
                        print("Skip already translated: {0}".format(source_node.text))
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

    def write_translated_texts_to_file(self, dest_lang_code):
        translation_file_path = self.get_generated_translation_file_path(
            dest_lang_code)

        with open(translation_file_path, 'rt', encoding="utf8") as f:
            tree = elementTree.parse(f)

        output_file_name = '{0}/translated_texts_{1}_{2}.txt'.format(
            self.output_dir, self.src_translation_file_name, dest_lang_code)
        print('Writing all translated text from {0} to file {1} ...'.format(
            translation_file_path, output_file_name))

        out_file = open(output_file_name, "w", encoding="utf-8")
        root = tree.getroot()

        for child_node in root:
            if child_node.tag == 'context':
                context_node = child_node
                for message_node in context_node.iter('message'):
                    source_node = message_node.find('source')
                    translate_node = message_node.find('translation')
                    if translate_node is not None:
                        try:
                            out_file.write('{0}:{1}\n'.format(
                                source_node.text, translate_node.text))
                        except Exception as e:
                            print('Exception during writing of {0} to file. Exception : {1}'.format(
                                source_node.text, str(e)))
        out_file.close()
