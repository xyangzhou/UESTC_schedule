from src.scheduleGenerator import scheduleGenerator
from tools.UESTC_login.utils import load_json, save_json, JSON2CSV, JSON2ICS, mkdirp
import os


def main(args):
    cfg = load_json(args.config_path)
    
    week = args.week
    try: 
        week = int(week)
    except ValueError:
        week = week.split('-')
        week = [int(w) for w in week]

    schedule_gen = scheduleGenerator(cfg['termInfoUrl'], cfg['weekInfoUrl'], 
                                     data=cfg['data'], headers=cfg['headers'], 
                                     cookies=args.cookies, 
                                     username=args.username, password=args.password,
                                     cas_baseurl=cfg['cas_baseurl'], cas_header=cfg['cas_header'],
                                    )

    schedule_json = schedule_gen.getSchedule(args.year, args.term, week, afk=args.afk)
    
    output_dir = os.path.dirname(args.output_name)
    if output_dir:
        mkdirp(output_dir)

    save_json(schedule_json, args.output_name + '.json')
    print(f"\033[32mSchedule generated, saving to {args.output_name}.json\033[0m")
    # schedule_json = load_json('schedule.json')
    JSON2ICS(schedule_json, cfg["courseTime"], args.output_name + '.ics')
    print(f"\033[32mCreating Canlendar events to {args.output_name}.ics\033[0m")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate a schedule for a given term and weeks')
    parser.add_argument('-y', '--year', type=str, help='The year of the term, format of XXXX-XXXX, e.g., 2024-2025', required=True)
    parser.add_argument('-t', '--term', type=int, choices=[1, 2], help='The term number, choose from 1, 2', required=True)
    parser.add_argument('-w', '--week', type=str, help='The week number, format of Int or Int-Int, e.g., 1 and 1-3. If do not specified or specified as -1, get all of the weeks.', default=-1)
    parser.add_argument('-c', '--cookies', type=str, help='The cookies for the schedule website, the value of eai-sess in https://mapp.uestc.edu.cn/site/weekschedule/index')
    parser.add_argument('-f', '--config_path', type=str, default='configs/config.json', help='The path to the config file')
    parser.add_argument('-o', '--output_name', type=str, default='schedule', help='The output file path, default is schedule which means ./schedule.json and ./schedule.ics')
    parser.add_argument('--afk', type=float, default=0.1, help='The time to wait between requests by weeks, default is 0.1s')
    parser.add_argument('--username', type=str, help='The username for https://eportal.uestc.edu.cn/')
    parser.add_argument('--password', type=str, help='The password for https://eportal.uestc.edu.cn/')
    parser.add_argument('--enable_pwd', action="store_true", help="Enable password login, if not set, use cookies login. If set, username and password are required.")
    args = parser.parse_args()
    if args.enable_pwd:
        args.cookies = None
        assert args.username is not None, "If enable_pwd, username is required, use --username"
        assert args.password is not None, "If enable_pwd, password is required, use --password"
    if not args.enable_pwd:
        assert args.cookies is not None, "If not enable_pwd, cookies are required, use -c / --cookies"
        
    main(args)