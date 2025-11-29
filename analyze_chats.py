#!/usr/bin/env python3
"""
Chat History Analytics Tool
Analyze chat logs for insights and improvements
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

class ChatAnalyzer:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        
    def load_date_file(self, date_str):
        """Load a specific date file (YYYY-MM-DD format)"""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        month_folder = date_obj.strftime('%Y-%m')
        day_file = date_obj.strftime('%d-%m-%Y') + '.json'
        
        file_path = os.path.join(self.data_dir, month_folder, day_file)
        
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def get_all_files(self):
        """Get all chat history files"""
        files = []
        for month_folder in os.listdir(self.data_dir):
            month_path = os.path.join(self.data_dir, month_folder)
            if os.path.isdir(month_path):
                for day_file in os.listdir(month_path):
                    if day_file.endswith('.json'):
                        files.append(os.path.join(month_path, day_file))
        return sorted(files)
    
    def daily_summary(self, date_str):
        """Get summary for a specific day"""
        data = self.load_date_file(date_str)
        if not data:
            print(f"❌ No data found for {date_str}")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 Daily Summary for {date_str}")
        print(f"{'='*60}\n")
        
        stats = data.get('daily_stats', {})
        print(f"📈 Overall Stats:")
        print(f"   Total Messages: {stats.get('total_messages', 0)}")
        print(f"   Total Sessions: {stats.get('total_sessions', 0)}")
        print(f"   👤 Authenticated: {stats.get('authenticated_sessions', 0)}")
        print(f"   👻 Anonymous: {stats.get('anonymous_sessions', 0)}")
        
        # Session breakdown
        sessions = data.get('sessions', {})
        print(f"\n🗂️  Session Details:")
        
        security_levels = defaultdict(int)
        languages = defaultdict(int)
        
        for session_id, session in sessions.items():
            msg_count = session.get('total_messages', 0)
            is_anon = "👻" if session.get('is_anonymous') else "👤"
            lang = session.get('language', 'EN')
            
            print(f"   {is_anon} {session_id[:30]}: {msg_count} msgs | {lang}")
            
            # Aggregate stats
            languages[lang] += 1
            for level, count in session.get('message_count_by_level', {}).items():
                security_levels[level] += count
        
        print(f"\n🔒 Security Level Distribution:")
        for level in ['low', 'mid', 'high', 'critical']:
            count = security_levels.get(level, 0)
            bar = '█' * (count // 2) if count > 0 else ''
            print(f"   {level.upper():10} | {count:3} | {bar}")
        
        print(f"\n🌐 Language Distribution:")
        for lang, count in languages.items():
            print(f"   {lang}: {count} sessions")
        
        print(f"\n{'='*60}\n")
    
    def weekly_summary(self, start_date_str):
        """Get summary for a week starting from date"""
        start = datetime.strptime(start_date_str, '%Y-%m-%d')
        
        print(f"\n{'='*60}")
        print(f"📊 Weekly Summary ({start_date_str} to {(start + timedelta(days=6)).strftime('%Y-%m-%d')})")
        print(f"{'='*60}\n")
        
        total_messages = 0
        total_sessions = 0
        total_anonymous = 0
        total_authenticated = 0
        
        for i in range(7):
            date = start + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            data = self.load_date_file(date_str)
            
            if data:
                stats = data.get('daily_stats', {})
                total_messages += stats.get('total_messages', 0)
                total_sessions += stats.get('total_sessions', 0)
                total_anonymous += stats.get('anonymous_sessions', 0)
                total_authenticated += stats.get('authenticated_sessions', 0)
                
                print(f"📅 {date_str}: {stats.get('total_messages', 0)} msgs, {stats.get('total_sessions', 0)} sessions")
        
        print(f"\n📊 Week Totals:")
        print(f"   Messages: {total_messages}")
        print(f"   Sessions: {total_sessions}")
        print(f"   👤 Authenticated: {total_authenticated}")
        print(f"   👻 Anonymous: {total_anonymous}")
        
        if total_sessions > 0:
            print(f"\n📈 Averages:")
            print(f"   Messages per session: {total_messages / total_sessions:.1f}")
            print(f"   Anonymous rate: {(total_anonymous / total_sessions) * 100:.1f}%")
        
        print(f"\n{'='*60}\n")
    
    def find_critical_messages(self, date_str):
        """Find all critical security level messages"""
        data = self.load_date_file(date_str)
        if not data:
            print(f"❌ No data found for {date_str}")
            return
        
        print(f"\n{'='*60}")
        print(f"🔴 Critical Messages for {date_str}")
        print(f"{'='*60}\n")
        
        found = False
        sessions = data.get('sessions', {})
        
        for session_id, session in sessions.items():
            critical_msgs = [m for m in session.get('messages', []) 
                           if m.get('level') == 'critical' and m.get('role') == 'user']
            
            if critical_msgs:
                found = True
                user_id = session.get('user_id', 'unknown')
                print(f"📍 Session: {session_id}")
                print(f"   User: {user_id}")
                print(f"   Language: {session.get('language', 'EN')}")
                
                for msg in critical_msgs:
                    timestamp = msg.get('timestamp', 'N/A')
                    content = msg.get('content', '')[:100]
                    print(f"   ⚠️  [{timestamp}] {content}...")
                print()
        
        if not found:
            print("✅ No critical messages found for this date\n")
        
        print(f"{'='*60}\n")
    
    def power_users(self, date_str, min_messages=10):
        """Find power users (users with many messages)"""
        data = self.load_date_file(date_str)
        if not data:
            print(f"❌ No data found for {date_str}")
            return
        
        print(f"\n{'='*60}")
        print(f"⭐ Power Users for {date_str} (>{min_messages} messages)")
        print(f"{'='*60}\n")
        
        sessions = data.get('sessions', {})
        power_sessions = [(sid, s) for sid, s in sessions.items() 
                         if s.get('total_messages', 0) > min_messages]
        
        power_sessions.sort(key=lambda x: x[1].get('total_messages', 0), reverse=True)
        
        if not power_sessions:
            print(f"📊 No users with more than {min_messages} messages\n")
        else:
            for session_id, session in power_sessions:
                user_id = session.get('user_id', 'anonymous')
                msg_count = session.get('total_messages', 0)
                duration = self._calculate_duration(session)
                
                print(f"👤 User ID: {user_id}")
                print(f"   Session: {session_id[:40]}")
                print(f"   Messages: {msg_count}")
                print(f"   Duration: {duration}")
                print(f"   Language: {session.get('language', 'EN')}")
                print(f"   Security breakdown: {session.get('message_count_by_level', {})}")
                print()
        
        print(f"{'='*60}\n")
    
    def _calculate_duration(self, session):
        """Calculate session duration"""
        try:
            start = datetime.fromisoformat(session.get('started_at', ''))
            end = datetime.fromisoformat(session.get('last_activity', ''))
            duration = end - start
            
            minutes = int(duration.total_seconds() / 60)
            if minutes < 1:
                return "< 1 minute"
            elif minutes < 60:
                return f"{minutes} minutes"
            else:
                hours = minutes // 60
                mins = minutes % 60
                return f"{hours}h {mins}m"
        except:
            return "Unknown"
    
    def export_to_csv(self, date_str, output_file):
        """Export day's data to CSV for analysis"""
        import csv
        
        data = self.load_date_file(date_str)
        if not data:
            print(f"❌ No data found for {date_str}")
            return
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['session_id', 'user_id', 'is_anonymous', 'language', 
                         'timestamp', 'role', 'content', 'level']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            sessions = data.get('sessions', {})
            for session_id, session in sessions.items():
                for msg in session.get('messages', []):
                    writer.writerow({
                        'session_id': session_id,
                        'user_id': session.get('user_id', ''),
                        'is_anonymous': session.get('is_anonymous', ''),
                        'language': session.get('language', ''),
                        'timestamp': msg.get('timestamp', ''),
                        'role': msg.get('role', ''),
                        'content': msg.get('content', ''),
                        'level': msg.get('level', '')
                    })
        
        print(f"✅ Exported to {output_file}\n")


def main():
    """Main CLI interface"""
    import sys
    
    analyzer = ChatAnalyzer()
    
    if len(sys.argv) < 2:
        print("""
Usage:
  python analyze_chats.py daily YYYY-MM-DD          # Daily summary
  python analyze_chats.py weekly YYYY-MM-DD         # Weekly summary (7 days from date)
  python analyze_chats.py critical YYYY-MM-DD       # Find critical messages
  python analyze_chats.py power YYYY-MM-DD [min]    # Power users (default: 10 msgs)
  python analyze_chats.py export YYYY-MM-DD file.csv # Export to CSV

Examples:
  python analyze_chats.py daily 2025-11-27
  python analyze_chats.py weekly 2025-11-20
  python analyze_chats.py critical 2025-11-27
  python analyze_chats.py power 2025-11-27 15
  python analyze_chats.py export 2025-11-27 output.csv
        """)
        return
    
    command = sys.argv[1]
    
    if command == "daily" and len(sys.argv) >= 3:
        analyzer.daily_summary(sys.argv[2])
    
    elif command == "weekly" and len(sys.argv) >= 3:
        analyzer.weekly_summary(sys.argv[2])
    
    elif command == "critical" and len(sys.argv) >= 3:
        analyzer.find_critical_messages(sys.argv[2])
    
    elif command == "power" and len(sys.argv) >= 3:
        min_msgs = int(sys.argv[3]) if len(sys.argv) >= 4 else 10
        analyzer.power_users(sys.argv[2], min_msgs)
    
    elif command == "export" and len(sys.argv) >= 4:
        analyzer.export_to_csv(sys.argv[2], sys.argv[3])
    
    else:
        print("❌ Invalid command or missing arguments. Run without args for help.")


if __name__ == "__main__":
    main()
