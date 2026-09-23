import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from buscar_tags import ApiError, VisionApi, base_url, matched_tags, read_tags, scan


class SearchTests(unittest.TestCase):
    def test_url_and_txt(self):
        self.assertEqual(base_url('server'), 'https://server/PIVision/Utility/api/v1')
        self.assertEqual(base_url('https://server/Custom/Utility/api/v1/'), 'https://server/Custom/Utility/api/v1')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'tags.txt'
            path.write_text('\ufeff# comentario\nTAG\ntag\n\n', encoding='utf-8')
            self.assertEqual(read_tags(path), {'tag': 'TAG'})

    def test_exact_matching_and_af(self):
        tags = {'tag': 'TAG', r'\\srv\tag': 'qualified'}
        self.assertEqual(set(matched_tags(r'pi:\\srv\TAG?abc', tags)), {'TAG', 'qualified'})
        self.assertEqual(matched_tags(r'pi:\\srv\TAG10', tags), [])
        self.assertEqual(matched_tags(r'af:\\srv\db\asset|TAG', tags), [])
        self.assertEqual(set(matched_tags(r'pi:\\srv\T%41G', tags)), {'TAG', 'qualified'})

    def test_pagination(self):
        session = Mock()
        session.get.side_effect = [Mock(status_code=200, json=Mock(return_value=p)) for p in [
            {'Items': [{'Id': 1}], 'HasMore': True},
            {'Items': [{'Id': 2}], 'HasMore': False},
        ]]
        api = VisionApi('server', session)
        self.assertEqual([i['Id'] for i in api.items('folders', 7)], [1, 2])
        self.assertEqual(session.get.call_args.kwargs['params'], {'Skip': 1, 'Count': 100, 'FolderId': 7})

    def test_invalid_pagination(self):
        for page in [None, {}, {'Items': [], 'HasMore': True}, {'Items': [{'Id': 1}], 'HasMore': True}]:
            session = Mock()
            session.get.return_value = Mock(status_code=200, json=Mock(return_value=page))
            with self.assertRaises(ApiError):
                list(VisionApi('server', session).items('displays'))

    def test_tree_root_unorganized_duplicates_and_failure(self):
        api = Mock(url='https://server/PIVision/Utility/api/v1')
        def items(endpoint, folder=None):
            if endpoint == 'folders':
                return iter({None: [{'Id': 1, 'Name': 'A'}], 1: [{'Id': 2, 'Name': 'B'}], 2: []}[folder])
            return iter({None: [{'Id': 10}], 1: [{'Id': 11}], 2: [{'Id': 12}],
                         'Unorganized': [{'Id': 10}, {'Id': 13}]}[folder])
        api.items.side_effect = items
        def export(endpoint):
            if endpoint == 'displays/11/export':
                raise ApiError('HTTP 403')
            return {'Display': {'Symbols': [{'Name': 's', 'SymbolType': 'group', 'children': [
                {'DataSources': [r'pi:\\srv\TAG', r'pi:\\srv\TAG']}
            ]}]}}
        api.get.side_effect = export
        rows = []
        result = scan(api, {'tag': 'TAG'}, rows.append)
        self.assertFalse(result['completo'])
        self.assertEqual(result['displays_analisados'], 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual({r[3] for r in rows}, {'/', '/A/B', '/[Unorganized]'})
        self.assertEqual(result['tags_encontradas'], ['TAG'])
        self.assertEqual(len(result['erros']), 1)

    def test_folder_failure_still_checks_other_folders(self):
        api = Mock(url='https://server/PIVision/Utility/api/v1')
        def items(endpoint, folder=None):
            if endpoint == 'folders':
                raise ApiError('HTTP 403')
            return iter([])
        api.items.side_effect = items
        result = scan(api, {'tag': 'TAG'}, lambda row: None)
        self.assertFalse(result['completo'])
        self.assertEqual(result['tags_sem_ocorrencias_observadas'], ['TAG'])


if __name__ == '__main__':
    unittest.main()
