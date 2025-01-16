from datetime import datetime, timedelta

from environs import Env
from requests.exceptions import RequestException
from terminaltables import AsciiTable

import requests


LANGUAGES = [
    'Python',
    'Java',
    'JavaScript',
    'Ruby',
    'PHP',
    'C++',
    'C#',
    'C',
    'Go',
]


def get_hh_vacancies(language):
    url = 'https://api.hh.ru/vacancies'
    date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    page = 0
    pages_number = 1

    params = {
        'page': page,
        'text': f'Программист {language}',
        'area': '1',
        'date_from': date_from,
    }

    vacancies = []
    while page < pages_number:
        page_response = requests.get(url, params=params)
        page_response.raise_for_status()

        page_payload = page_response.json()
        pages_number = page_payload['pages']
        page += 1

        vacancies.extend(page_payload['items'])

    return vacancies


def get_sj_vacancies(language):
    env = Env()
    env.read_env()
    api_key = env.str('SUPER_JOB_KEY')

    url = 'https://api.superjob.ru/2.0/vacancies/'

    headers = {
        'X-Api-App-Id': api_key,
    }

    date_from = int((datetime.now() - timedelta(days=30)).timestamp())

    page = 0
    more_pages = True
    vacancies = []

    while more_pages:
        params = {
            'keywords': [f'Программист {language}'],
            'town': 'Москва',
            'date_published_from': date_from,
            'catalogues': 48,
            'page': page,
        }

        page_response = requests.get(url, headers=headers, params=params)
        page_response.raise_for_status()

        page_payload = page_response.json()
        vacancies.extend(page_payload['objects'])
        more_pages = page_payload['more']
        page += 1

    return vacancies


def predict_salary(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    elif salary_from:
        return salary_from * 1.2
    elif salary_to:
        return salary_to * 0.8
    return None


def predict_rub_salary_hh(vacancy):
    salary = vacancy.get('salary')
    if not salary or salary.get('currency') != 'RUR':
        return None
    return predict_salary(
        salary.get('from'),
        salary.get('to'),
    )


def predict_rub_salary_sj(vacancy):
    if vacancy.get('currency') != 'rub':
        return None
    return predict_salary(
        vacancy.get('payment_from'),
        vacancy.get('payment_to'),
    )


def calculate_statistics_hh(languages):
    statistics = {}

    for language in languages:
        vacancies = get_hh_vacancies(language)
        salaries = []
        for vacancy in vacancies:
            salary = predict_rub_salary_hh(vacancy)
            if salary:
                salaries.append(salary)

        statistics[language] = {
            'vacancies_found': len(vacancies),
            'vacancies_processed': len(salaries),
            'average_salary': (
                int(sum(salaries) / len(salaries)) if salaries
                else None
            ),
        }

    return statistics


def calculate_statistics_sj(languages):
    statistics = {}

    for language in languages:
        vacancies = get_sj_vacancies(language)
        salaries = []

        for vacancy in vacancies:
            salary = predict_rub_salary_sj(vacancy)
            if salary:
                salaries.append(salary)

        statistics[language] = {
            'vacancies_found': len(vacancies),
            'vacancies_processed': len(salaries),
            'average_salary': (
                int(sum(salaries) / len(salaries)) if salaries
                else None
            ),
        }

    return statistics


def print_statistics_table(statistics, platform):
    table_contents = [
        ['Язык программирования',
         'Вакансий найдено',
         'Вакансий обработано',
         'Средняя зарплата']
    ]

    for language, stats in statistics.items():
        table_contents.append([
            language,
            stats['vacancies_found'],
            stats['vacancies_processed'],
            stats['average_salary'],
        ])

    table = AsciiTable(table_contents, f'{platform} Moscow')
    print(table.table)


def main():
    try:
        hh_statistics = calculate_statistics_hh(LANGUAGES)
        sj_statistics = calculate_statistics_sj(LANGUAGES)

        print_statistics_table(hh_statistics, 'HeadHunter')
        print_statistics_table(sj_statistics, 'SuperJob')

    except requests.exceptions.RequestException as request_error:
        print(f'Ошибка при выполнении запроса: {request_error}')
    except (KeyError, ValueError) as data_error:
        print(f'Ошибка обработки данных: {data_error}')
    except Exception as error:
        print(f'Произошла непредвиденная ошибка: {error}')


if __name__ == '__main__':
    main()
