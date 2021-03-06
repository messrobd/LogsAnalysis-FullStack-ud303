#!/usr/bin/env python3
import psycopg2
import sys
import getopt
import os

DBName = 'news'


class Report():
    def __init__(self, title, formatter, query, query_args=None):
        self.title = title
        self.formatter = formatter
        if query_args:
            self.query = query % query_args
        else:
            self.query = query

    def make_report(self):
        '''Submit query and yield lines to print methods'''
        for line in get_data(self.query):
            yield line


def get_data(query):
    '''Connect to database and return query data to caller'''
    connection = psycopg2.connect(dbname=DBName)
    cursor = connection.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    connection.close()
    return data


def print_report(report, file_out):
    '''Call report and print to file or console'''
    if file_out:
        # Write file to cwd:
        report_file = open(report.title.replace(' ', '_') + '.txt', 'w')
        report_file.write(report.title + '\n')
        for line in report.make_report():
            report_file.write(report.formatter(line) + '\n')
        report_file.close()
    else:
        print(report.title)
        for line in report.make_report():
            print(report.formatter(line))


# Define reoprts:
top_arts_query = '''
    select title, count(*) as num
        from articles, log
        where path like '%' || slug
        group by articles.id
        order by num desc
        limit 3; '''


def top_arts_formatter(line):
    '''Takes a raw line from the db query output and retuns a line formatted
    for the articles report'''
    line_template = '"%s" - %s views'
    return line_template % line


top_articles = Report('Top 3 articles', top_arts_formatter, top_arts_query)


top_auths_query = '''
    select authors.name, count(*) as num
        from articles, log, authors
        where path like '%' || slug
            and author = authors.id
        group by authors.name
        order by num desc; '''


def top_auths_formatter(line):
    '''Takes a raw line from the db query output and retuns a line formatted
    for the authors report'''
    line_template = '%s - %s views'
    return line_template % line


top_authors = Report('Top authors', top_auths_formatter, top_auths_query)


bad_days_query = '''
select *
    from
    (select err_n_daily.date, (cast(errs as real) / cast(rqs as real)) as err_f
        from
        (select date_trunc('day', time) as date, count(*) as rqs
            from log
            group by date) as rq_n_daily,
        (select date_trunc('day', time) as date, count(*) as errs
            from log
            where not status = '200 OK'
            group by date) as err_n_daily
        where err_n_daily.date = rq_n_daily.date) as err_f_daily
    where err_f > %s; '''


bad_day_tol = 0.01


def bad_days_formatter(line):
    '''Takes a raw line from the db query output and retuns a line formatted
    for the bad days report'''
    line_template = '%s - %s%% errors'
    (timestamptz, error_frac) = line
    date = timestamptz.strftime('%B %d, %Y')
    error_percent = round(error_frac * 100, 2)
    return line_template % (date, error_percent)


bad_days = Report('Bad days', bad_days_formatter, bad_days_query, bad_day_tol)


reports = {
    1: top_articles,
    2: top_authors,
    3: bad_days
}


# Main program:
def main(options, file_out=False):
    '''
    1. Interpret command line. The user may enter the -f option to write to
    file instead of console
    2. Show report options. Give the user multiple attempts to provide a valid
    input
    3. Print the selected report '''
    try:
        opts, args = getopt.getopt(options, 'f')
    except getopt.GetoptError:
        print('usage: logs_analysis.py [-f]')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-f':
            file_out = True
    print('Select a report:')
    for report in reports:
        print('%s - %s' % (report, reports[report].title))
    valid_report = False
    while not valid_report:
        choice = input()
        try:
            report = reports[int(choice)]
        except (KeyError, ValueError):
            print('Please pick a number 1 - 3')
        else:
            valid_report = True
    print_report(report, file_out)


if __name__ == '__main__':
    main(sys.argv[1:])
