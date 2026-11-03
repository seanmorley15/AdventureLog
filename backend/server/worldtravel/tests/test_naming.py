from django.test import SimpleTestCase

from worldtravel.naming import name_keys, name_words, normalize_name


class NormalizeNameTests(SimpleTestCase):
    def test_accents_case_and_punctuation_are_folded(self):
        self.assertEqual(normalize_name("Saint-Barthélemy"), "saintbarthelemy")
        self.assertEqual(normalize_name("  St. John's "), "stjohns")

    def test_letters_that_are_not_split_into_base_and_accent_are_transliterated(self):
        self.assertEqual(normalize_name("Bouvetøya"), "bouvetoya")
        self.assertEqual(normalize_name("Straße"), "strasse")
        self.assertEqual(normalize_name("Þingvellir"), "thingvellir")

    def test_names_without_latin_letters_keep_their_own_letters(self):
        # They must not all collapse to the same empty key.
        self.assertEqual(normalize_name("Октябрьский"), "октябрьский")
        self.assertNotEqual(normalize_name("Арачиново"), normalize_name("Петровец"))
        self.assertTrue(normalize_name("سروستان"))

    def test_punctuation_alone_is_an_empty_key(self):
        self.assertEqual(normalize_name("-- "), "")


class NameKeysTests(SimpleTestCase):
    def test_generic_division_words_are_optional(self):
        keys = name_keys("Saint Peter Parish")
        self.assertIn("saintpeter", keys)
        self.assertIn("stpeter", keys)

    def test_prefixes_that_look_like_generic_words_are_left_alone(self):
        self.assertEqual(name_keys("Lamu"), {"lamu"})
        self.assertEqual(name_keys("Laayoune"), {"laayoune"})

    def test_each_alternative_is_a_key(self):
        keys = name_keys("Komuna e Prishtinës / Opština Priština")
        self.assertIn("opstinapristina", keys)

    def test_alternatives_can_be_turned_off(self):
        self.assertIn("miquelon", name_keys("Saint Pierre and Miquelon"))
        self.assertNotIn("miquelon", name_keys("Saint Pierre and Miquelon", alternatives=False))

    def test_a_name_that_is_only_generic_words_has_no_stripped_key(self):
        self.assertEqual(name_keys("Islands"), {"islands"})

    def test_none_has_no_keys(self):
        self.assertEqual(name_keys(None), set())


class NameWordsTests(SimpleTestCase):
    def test_filler_words_do_not_count(self):
        self.assertEqual(name_words("Saint Pierre and Miquelon"), {"pierre", "miquelon"})
