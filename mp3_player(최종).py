import sys
import os
import json
import re
import threading
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import *
from PyQt5 import uic
import mutagen
from mutagen.id3 import ID3
from mutagen.mp3 import MP3

# yt-dlp 라이브러리 import
try:
    import yt_dlp
except ImportError:
    print("yt-dlp가 설치되지 않았습니다. 'pip install yt-dlp' 명령어로 설치해주세요.")
    sys.exit(1)

class SearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YouTube 음악 검색 및 다운로드")
        self.setModal(True)
        self.resize(700, 500)
        self.selected_item = None
        self.download_thread = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # 검색 입력창과 버튼을 포함하는 수평 레이아웃
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색할 음악 제목을 입력하세요... (예: 아이유 미인)")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #FFFFFF;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
                background-color: #222;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #FFFFFF;
                
                
            }
        """)
        self.search_input.returnPressed.connect(self.search_music)

        self.search_btn = QPushButton("🔍 검색")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.search_btn.clicked.connect(self.search_music)
        self.search_btn.setFixedWidth(100)

        search_layout.addWidget(self.search_input, stretch=3)
        search_layout.addWidget(self.search_btn)

        # 검색 결과 리스트
        self.result_list = QListWidget()
        self.result_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #333;
                border-radius: 5px;
                padding: 5px;
                background-color: #222;
                color: #fff;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #333;
            }
        """)
        self.result_list.itemDoubleClicked.connect(self.download_selected)
        self.result_list.setAlternatingRowColors(False)
        self.result_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # 진행 상황 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #333;
                border-radius: 5px;
                text-align: center;
                font-size: 14px;
                background-color: #222;
                color: #fff;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)
        self.progress_bar.setVisible(False)

        self.status_label = QLabel("검색할 음악을 입력하고 검색 버튼을 눌러주세요.")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #bbb;
                padding: 5px;
            }
        """)

        # 버튼들
        button_layout = QHBoxLayout()
        self.download_btn = QPushButton("📥 다운로드")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.download_btn.clicked.connect(self.download_selected)
        self.download_btn.setEnabled(False)

        self.cancel_btn = QPushButton("❌ 취소")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.download_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(search_layout)
        layout.addWidget(QLabel("🎵 검색 결과 (더블클릭으로 다운로드):"))
        layout.addWidget(self.result_list, stretch=2)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 리스트 선택 변경 이벤트
        self.result_list.itemSelectionChanged.connect(self.on_selection_changed)

    def on_selection_changed(self):
        self.download_btn.setEnabled(len(self.result_list.selectedItems()) > 0)

    def search_music(self):
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "경고", "검색어를 입력해주세요.")
            return

        self.search_btn.setEnabled(False)
        self.result_list.clear()
        self.status_label.setText("🔍 YouTube에서 검색 중...")

        self.search_thread = SearchThread(query)
        self.search_thread.results_ready.connect(self.display_results)
        self.search_thread.error_occurred.connect(self.handle_search_error)
        self.search_thread.start()

    def display_results(self, results):
        self.result_list.clear()
        for item in results:
            title = item.get('title', 'Unknown Title')
            duration = item.get('duration_string', 'Unknown')
            uploader = item.get('uploader', 'Unknown')

            display_text = f"🎵 {title}\n📺 {uploader} • ⏱️ {duration}"

            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, item)
            self.result_list.addItem(list_item)

        self.search_btn.setEnabled(True)
        if results:
            self.status_label.setText(f"✅ {len(results)}개의 결과를 찾았습니다. 다운로드할 음악을 선택해주세요.")
        else:
            self.status_label.setText("❌ 검색 결과가 없습니다. 다른 검색어를 시도해보세요.")

    def handle_search_error(self, error_msg):
        self.search_btn.setEnabled(True)
        self.status_label.setText("❌ 검색 실패")
        QMessageBox.critical(self, "오류", f"검색 중 오류가 발생했습니다:\n{error_msg}")

    def download_selected(self):
        current_item = self.result_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "경고", "다운로드할 음악을 선택해주세요.")
            return

        self.selected_item = current_item.data(Qt.UserRole)
        self.start_download()

    def start_download(self):
        if not self.selected_item:
            return

        self.download_btn.setEnabled(False)
        self.search_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("📥 다운로드 준비 중...")

        self.download_thread = DownloadThread(self.selected_item)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_completed.connect(self.download_finished)
        self.download_thread.download_completed.connect(self.parent().download_completed)  # MusicPlayer에 연결
        self.download_thread.error_occurred.connect(self.handle_download_error)
        self.download_thread.start()

    def update_progress(self, value, status):
        self.progress_bar.setValue(value)
        self.status_label.setText(status)

    def download_finished(self, file_path):
        self.progress_bar.setVisible(False)
        self.status_label.setText("✅ 다운로드 완료!")
        self.download_btn.setEnabled(True)
        self.search_btn.setEnabled(True)
        self.accept()  # 창 자동 닫기, 메시지 상자 제거


    def handle_download_error(self, error_msg):
        self.download_btn.setEnabled(True)
        self.search_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ 다운로드 실패")
        QMessageBox.critical(self, "오류", f"다운로드 중 오류가 발생했습니다:\n{error_msg}")

    def closeEvent(self, event):
        if self.download_thread and self.download_thread.isRunning():
            reply = QMessageBox.question(self, '확인', '다운로드가 진행 중입니다. 정말 취소하시겠습니까?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.download_thread.terminate()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

class SearchThread(QThread):
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            results = self.search_youtube(self.query)
            self.results_ready.emit(results)
        except Exception as e:
            self.error_occurred.emit(f"검색 중 오류 발생: {str(e)}")

    def search_youtube(self, query):
        """YouTube에서 음악 검색"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'default_search': f'ytsearch10:{query}',  # 명시적 검색 쿼리
            'extract_flat': True,  # 최소한의 데이터만 추출
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                print(f"검색 쿼리: {query}")  # 디버깅용 로그
                search_results = ydl.extract_info(f"ytsearch10:{query}", download=False)
                if 'entries' in search_results and search_results['entries']:
                    results = []
                    for entry in search_results['entries']:
                        if entry and 'id' in entry:
                            results.append({
                                'id': entry.get('id'),
                                'title': entry.get('title', 'Unknown Title'),
                                'uploader': entry.get('uploader', 'Unknown'),
                                'duration': entry.get('duration'),
                                'duration_string': entry.get('duration_string', 'Unknown'),
                                'url': entry.get('webpage_url'),
                                'view_count': entry.get('view_count', 0),
                                'like_count': entry.get('like_count', 0)
                            })
                    results.sort(key=lambda x: x.get('view_count', 0), reverse=True)
                    print(f"검색 결과 개수: {len(results)}")  # 디버깅용 로그
                    return results[:10]
                print("검색 결과 없음")
                return []
            except yt_dlp.utils.DownloadError as de:
                raise Exception(f"다운로드 오류: {str(de)}")
            except Exception as e:
                raise Exception(f"알 수 없는 오류: {str(e)}")

class DownloadThread(QThread):
    progress_updated = pyqtSignal(int, str)
    download_completed = pyqtSignal(tuple)  # 튜플로 정의
    error_occurred = pyqtSignal(str)

    def __init__(self, item_data):
        super().__init__()
        self.item_data = item_data
        self.is_running = True

    def run(self):
        try:
            download_dir = r"C:\Users\USER\Downloads\music"
            if not os.path.exists(download_dir):
                os.makedirs(download_dir, exist_ok=True)

            safe_title = re.sub(r'[<>:"/\\|?*()\[\],\'\.]', '', self.item_data['title'])[:40]
            safe_title = safe_title.replace('\n', ' ').strip()

            self.progress_updated.emit(10, "🔍 비디오 정보 가져오는 중...")

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(download_dir, f'{safe_title}.%(ext)s'),
                'ffmpeg_location': 'C:/ffmpeg/bin',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'postprocessor_args': [
                    '-c:a', 'mp3', '-b:a', '192k', '-ar', '44100', '-ac', '2', '-vn'
                ],
                'prefer_ffmpeg': True,
                'keepvideo': False,
                'writethumbnail': True,
                'postprocessor_errors': 'warn',
                'ignoreerrors': True,
            }

            def progress_hook(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d:
                        percent = int(d['downloaded_bytes'] / d['total_bytes'] * 100)
                        self.progress_updated.emit(percent, f"📥 다운로드 중... {percent}%")
                    elif 'total_bytes_estimate' in d:
                        percent = int(d['downloaded_bytes'] / d['total_bytes_estimate'] * 100)
                        self.progress_updated.emit(percent, f"📥 다운로드 중... {percent}%")
                    else:
                        self.progress_updated.emit(50, "📥 다운로드 중...")
                elif d['status'] == 'finished':
                    self.progress_updated.emit(90, "🔄 MP3로 변환 중...")

            ydl_opts['progress_hooks'] = [progress_hook]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_url = f"https://www.youtube.com/watch?v={self.item_data['id']}"
                print(f"다운로드 시작: {video_url}")
                ydl.download([video_url])
                print("다운로드 완료")

            expected_path = os.path.join(download_dir, f"{safe_title}.mp3")
            thumbnail_path = os.path.join(download_dir, f"{safe_title}.webp")
            if os.path.exists(expected_path):
                self.progress_updated.emit(100, "✅ 완료!")
                self.download_completed.emit((expected_path, thumbnail_path))  # 튜플 emit
                print(f"[DEBUG] download_completed emit: {(expected_path, thumbnail_path)}")
            else:
                raise Exception("다운로드된 파일을 찾을 수 없습니다.")

        except Exception as e:
            print(f"예외 발생: {str(e)}")
            self.error_occurred.emit(f"다운로드 오류: {str(e)}")

class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()

        uic.loadUi('mp3_player.ui', self)
        self.setWindowTitle('MP3_Player')

        self.central_widget = self.findChild(QWidget, "centralWidget")
        self.slider_music = self.findChild(QSlider, "Slider_Mus")
        self.slider_volume = self.findChild(QSlider, "Slider_Vol")
        self.btn_add = self.findChild(QPushButton, "btn_Add")
        self.btn_forward = self.findChild(QPushButton, "btn_Forward")
        self.btn_past = self.findChild(QPushButton, "btn_Past")
        self.btn_play = self.findChild(QPushButton, "btn_Play")
        self.btn_delete = self.findChild(QPushButton, "btn_delete")
        self.btn_Down = self.findChild(QPushButton, "btn_Down")
        self.lbl_music = self.findChild(QLabel, "lbl_Music")
        self.lbl_name = self.findChild(QLabel, "lbl_Name")
        self.lbl_Time = self.findChild(QLabel, "lbl_Time")
        self.btn_list = self.findChild(QPushButton, "btn_List")
        self.lbl_exit = self.findChild(QPushButton, "lbl_Exit")
        self.list_title = self.findChild(QLabel, "lbl_List")
        self.list_widget = self.findChild(QListWidget, "listWidget")

        self.player = QMediaPlayer()
        self.playlist = QMediaPlaylist()
        self.player.setPlaylist(self.playlist)

        self.current_song = ""
        self.is_initial_load = True  # UI 처음 뜰 때만 True

        self.is_playing = False
        self.current_index = -1
        self.songs_list = []

        self.is_compact_view = False
        self.compact_size = (400, 700)
        self.expanded_size = (750, 700)

        self.init_player()
        self.connect_signals()
        self.load_playlist()
        self.setup_download_feature()

    def setup_download_feature(self):
        if hasattr(self, 'btn_Down') and self.btn_Down:
            self.btn_Down.clicked.connect(self.open_download_dialog)
            self.btn_Down.setText("📥 다운로드")

    def open_download_dialog(self):
        # 기존 재생 상태 저장
        self._previous_state = {
            'position': self.player.position() if self.is_playing else -1,
            'index': self.current_index,
            'state': self.is_playing
        }
        print(
            f"[DEBUG] 저장된 이전 상태 - 위치: {self._previous_state['position']}ms, 인덱스: {self._previous_state['index']}, 상태: {'재생 중' if self._previous_state['state'] else '정지'}")

        dialog = SearchDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            if hasattr(dialog, 'download_thread') and dialog.download_thread:
                self.download_thread = dialog.download_thread
                self.download_thread.download_completed.connect(self.download_completed)

    def download_completed(self, file_path_tuple):
        print(f"[DEBUG] download_completed 호출됨: {file_path_tuple}")
        file_path, thumbnail_path = file_path_tuple
        print(f"[DEBUG] 다운로드 완료됨: {file_path}, 썸네일: {thumbnail_path}")
        if file_path not in self.songs_list:
            self.songs_list.append(file_path)
            display_name = self.get_song_display_name(file_path)
            self.list_widget.addItem(f"🎵 {display_name}")
            url = QUrl.fromLocalFile(file_path)
            self.playlist.addMedia(QMediaContent(url))
            self.save_playlist()
            self.list_widget.scrollToBottom()
        self.refresh_playlist()
        print(
            f"[DEBUG] 새 곡 추가됨, 현재 인덱스: {self.current_index}, 파일: {self.songs_list[self.current_index] if self.current_index >= 0 else '없음'}")
        # 기존 재생 유지, 새 곡은 자동 재생하지 않음
        self.load_album_art(self.songs_list[self.current_index] if self.current_index >= 0 else file_path)

    def refresh_playlist(self):
        print("[DEBUG] 플레이리스트 새로고침")

        self.list_widget.clear()
        self.playlist.clear()
        download_dir = r"C:\Users\USER\Downloads\music"
        existing_files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if f.endswith('.mp3')]
        self.songs_list = [f for f in self.songs_list if f in existing_files]  # 기존 파일 유지
        for file_path in self.songs_list:
            if os.path.exists(file_path):
                display_name = self.get_song_display_name(file_path)
                self.list_widget.addItem(f"🎵 {display_name}")
                url = QUrl.fromLocalFile(file_path)
                self.playlist.addMedia(QMediaContent(url))

        print(f"[DEBUG] list_widget 아이템 수: {self.list_widget.count()}")
        self.save_playlist()
        if self.songs_list and self.current_index == -1:
            self.current_index = 0

    def restore_position(self, position, state):
        """재생 위치 및 상태 복원"""
        if self.current_index >= 0 and self.current_index < len(self.songs_list):
            if os.path.exists(self.songs_list[self.current_index]):
                self.player.setPosition(position if position >= 0 else 0)
                if state:
                    self.player.play()
                    self.is_playing = True
                    self.btn_play.setText("⏸")
                else:
                    self.player.pause()
                    self.is_playing = False
                    self.btn_play.setText("▶")
                print(f"복원 완료 - 위치: {position}ms, 상태: {'재생 중' if state else '정지'}, 현재 위치: {self.player.position()}ms")
            else:
                print(f"[WARNING] 파일이 존재하지 않음: {self.songs_list[self.current_index]}")

    def load_current_song(self):
        if 0 <= self.current_index < len(self.songs_list):
            song_path = self.songs_list[self.current_index]
            if self.current_song == song_path:
                return
            self.current_song = song_path
            display_name = self.get_song_display_name(song_path)
            self.lbl_name.setText(display_name)
            self.load_album_art(song_path)
            self.list_widget.setCurrentRow(self.current_index)
            self.update_current_playing_label()
            url = QUrl.fromLocalFile(song_path)
            self.player.setMedia(QMediaContent(url))
            print(f"[DEBUG] 미디어 로드: {song_path}")
            if self.player.error() != QMediaPlayer.NoError:
                print(f"[ERROR] 미디어 로드 오류: {self.player.errorString()}")
                self.next_song()  # Skip invalid media
            elif self.is_playing:
                QTimer.singleShot(100, self.start_playback)

    def play_music(self, file_path):
        if not os.path.exists(file_path):
            print(f"[ERROR] 파일이 존재하지 않습니다: {file_path}")
            return
        print(f"[DEBUG] 재생 시도: {file_path}")
        self.current_index = len(self.songs_list) - 1  # Assuming new file is added last
        self.load_current_song()
        if self.is_playing:
            QTimer.singleShot(100, self.start_playback)


    def init_player(self):
        self.player.setVolume(70)
        self.slider_volume.setValue(70)
        self.playlist.setPlaybackMode(QMediaPlaylist.Loop)
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_position_from_timer)
        self.timer.start()

    def update_position_from_timer(self):
        position = self.player.position()
        self.update_position(position)

    def connect_signals(self):
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.stateChanged.connect(self.state_changed)
        self.player.mediaStatusChanged.connect(self.media_status_changed)

        self.slider_music.sliderMoved.connect(self.set_position)
        self.slider_volume.valueChanged.connect(self.set_volume)

        self.btn_past.clicked.connect(self.previous_song)
        self.btn_play.clicked.connect(self.toggle_playback)
        self.btn_forward.clicked.connect(self.next_song)
        self.btn_add.clicked.connect(self.add_files)
        self.btn_list.clicked.connect(self.toggle_playlist_view)
        self.lbl_exit.clicked.connect(self.toggle_playlist_view)
        self.btn_delete.clicked.connect(self.delete_selected_song)

        self.list_widget.itemDoubleClicked.connect(self.play_selected_song)
        self.playlist.currentIndexChanged.connect(self.playlist_position_changed)

    def toggle_playlist_view(self):
        if self.is_compact_view:
            self.list_widget.hide()
            QTimer.singleShot(1, lambda: self.resize(self.compact_size[0], self.compact_size[1]))
            self.btn_list.setText("📋 목록")
        else:
            self.list_widget.hide()
            self.list_widget.show()
            self.resize(self.expanded_size[0], self.expanded_size[1])
            self.btn_list.setText("📋 목록")
            self.update_current_playing_label()
        self.is_compact_view = not self.is_compact_view

    def save_playlist(self):
        with open("playlist.json", 'w') as f:
            json.dump(self.songs_list, f)

    def load_playlist(self):
        if os.path.exists("playlist.json"):
            try:
                with open("playlist.json", 'r') as f:
                    self.songs_list = json.load(f)
                    for file_path in self.songs_list:
                        if os.path.exists(file_path):
                            display_name = self.get_song_display_name(file_path)
                            self.list_widget.addItem(f"🎵 {display_name}")
                            url = QUrl.fromLocalFile(file_path)
                            self.playlist.addMedia(QMediaContent(url))
                        else:
                            self.songs_list.remove(file_path)
                    self.save_playlist()
                if self.songs_list:
                    self.current_index = 0
                    self.load_current_song()
            except Exception as e:
                self.songs_list = []

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "음악 파일 선택", "",
            "Audio Files (*.mp3 *.wav *.m4a *.flac *.ogg *.aac)"
        )
        for file_path in files:
            if file_path not in self.songs_list:
                self.songs_list.append(file_path)
                display_name = self.get_song_display_name(file_path)
                self.list_widget.addItem(f"🎵 {display_name}")
                url = QUrl.fromLocalFile(file_path)
                self.playlist.addMedia(QMediaContent(url))
        if self.songs_list and self.current_index == -1:
            self.current_index = 0
            self.load_current_song()
        self.save_playlist()

    def get_song_display_name(self, file_path):
        try:
            audio_file = mutagen.File(file_path, easy=True)
            if audio_file:
                title = audio_file.get('title', [None])[0]
                artist = audio_file.get('artist', [None])[0]
                if title:
                    if artist:
                        return f"{artist} - {title}"
                    return str(title)
            return os.path.splitext(os.path.basename(file_path))[0]
        except Exception as e:
            print(f"[ERROR] 메타데이터 읽기 실패: {file_path}, 오류: {e}")
            return os.path.splitext(os.path.basename(file_path))[0]

    def play_selected_song(self, item):
        index = self.list_widget.row(item)
        self.current_index = index
        self.playlist.setCurrentIndex(index)
        self.load_current_song()
        QTimer.singleShot(100, self.start_playback)

    def start_playback(self):
        if self.current_song:
            self.player.play()
            self.is_playing = True
            self.btn_play.setText("⏸")

    def load_current_song(self):
        if 0 <= self.current_index < len(self.songs_list):
            song_path = self.songs_list[self.current_index]
            if self.current_song == song_path:
                return
            self.current_song = song_path
            display_name = self.get_song_display_name(song_path)
            self.lbl_name.setText(display_name)
            self.load_album_art(song_path)
            self.list_widget.setCurrentRow(self.current_index)  # 현재 재생 곡을 선택 상태로 설정
            self.update_current_playing_label()
            url = QUrl.fromLocalFile(song_path)
            self.player.setMedia(QMediaContent(url))
            print(f"[DEBUG] 미디어 로드: {song_path}")
            if self.player.error() == QMediaPlayer.NoError:
                print("미디어 로드 성공, 재생 시도")
                self.player.play()  # 명시적 재생 시도
            else:
                print(f"미디어 로드 오류: {self.player.errorString()}")

    def load_album_art(self, file_path):
        try:
            # 별도 썸네일 파일 확인
            base_name = os.path.splitext(file_path)[0]
            for ext in ['.webp', '.jpg', '.png']:
                thumbnail_path = base_name + ext
                if os.path.exists(thumbnail_path):
                    pixmap = QPixmap(thumbnail_path)
                    scaled_pixmap = pixmap.scaled(270, 270, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.lbl_music.setPixmap(scaled_pixmap)
                    print(f"[DEBUG] 썸네일 로드 성공: {thumbnail_path}")
                    return

            # MP3 메타데이터에서 썸네일 확인
            audio_file = mutagen.File(file_path)
            if audio_file and hasattr(audio_file, 'tags') and audio_file.tags:
                for key in audio_file.tags:
                    if key.startswith('APIC'):
                        artwork = audio_file.tags[key].data
                        pixmap = QPixmap()
                        pixmap.loadFromData(artwork)
                        scaled_pixmap = pixmap.scaled(270, 270, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.lbl_music.setPixmap(scaled_pixmap)
                        print(f"[DEBUG] 메타데이터 썸네일 로드 성공")
                        return

            self.set_default_album_art()
            print("[DEBUG] 기본 앨범 아트 사용")
        except Exception as e:
            print(f"[ERROR] 앨범 아트 로드 실패: {e}")
            self.set_default_album_art()
    def set_default_album_art(self):
        pixmap = QPixmap("./images/music.jpg")
        self.lbl_music.setPixmap(pixmap)
        self.lbl_music.setScaledContents(True)

    def update_current_playing_label(self):
        if self.current_song:
            display_name = self.get_song_display_name(self.current_song)
            self.list_title.setText(f"재생 중: {display_name}")
        else:
            self.list_title.setText("재생 중: 없음")

    def toggle_playback(self):
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.btn_play.setText("▶")
        else:
            if self.current_song:
                self.player.play()
                self.is_playing = True
                self.btn_play.setText("⏸")
            elif self.songs_list:
                self.current_index = 0
                self.load_current_song()
                QTimer.singleShot(100, self.start_playback)

    def previous_song(self):
        if self.songs_list:
            self.current_index = (self.current_index - 1) % len(self.songs_list)
            self.playlist.setCurrentIndex(self.current_index)
            self.load_current_song()
            if self.is_playing:
                QTimer.singleShot(100, self.start_playback)

    def next_song(self):
        if self.songs_list:
            self.current_index = (self.current_index + 1) % len(self.songs_list)
            self.playlist.setCurrentIndex(self.current_index)
            self.load_current_song()
            if self.is_playing:
                QTimer.singleShot(100, self.start_playback)

    def playlist_position_changed(self, index):
        if 0 <= index < len(self.songs_list):
            self.current_index = index
            self.load_current_song()

    def set_volume(self, value):
        self.player.setVolume(value)

    def set_position(self, position):
        self.player.setPosition(position)

    def update_position(self, position):
        if not self.slider_music.isSliderDown():
            self.slider_music.setValue(position)
        duration = self.player.duration()
        if duration > 0:
            current_time = self.format_time(position)
            total_time = self.format_time(duration)
            self.lbl_Time.setText(f"{current_time} / {total_time}")
        else:
            self.lbl_Time.setText("00:00 / 00:00")

    def update_duration(self, duration):
        if duration > 0:
            self.slider_music.setRange(0, duration)
            self.lbl_Time.setText(f"00:00 / {self.format_time(duration)}")
        else:
            self.slider_music.setRange(0, 0)
            self.lbl_Time.setText("00:00 / 00:00")

    def state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.is_playing = True
            self.btn_play.setText("⏸")
            if 0 <= self.current_index < len(self.songs_list):
                self.list_widget.setCurrentRow(self.current_index)  # 재생 중일 때 강조
        elif state == QMediaPlayer.PausedState or state == QMediaPlayer.StoppedState:
            self.is_playing = False
            self.btn_play.setText("▶")

    def media_status_changed(self, status):
        print(f"미디어 상태 변경: {status}")
        if status == QMediaPlayer.LoadedMedia:
            print("미디어 로드 완료, 재생 준비")
            if self.is_playing and self.player.position() == 0:
                self.player.play()
            if 0 <= self.current_index < len(self.songs_list):
                self.list_widget.setCurrentRow(self.current_index)  # 로드 후 강조
        elif status == QMediaPlayer.InvalidMedia:
            print(f"유효하지 않은 미디어: {self.current_song}, 다음 곡으로 이동")
            self.next_song()
        elif status == QMediaPlayer.EndOfMedia:
            print("미디어 재생 완료, 다음 곡으로 이동")
            self.next_song()

    def format_time(self, ms):
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def closeEvent(self, event):
        self.player.stop()
        event.accept()

    def delete_selected_song(self):
        """선택된 곡 삭제"""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            row = self.list_widget.row(item)
            file_path = self.songs_list[row]
            self.list_widget.takeItem(row)
            del self.songs_list[row]
            self.playlist.removeMedia(row)
            # 삭제된 파일이 JSON에 남아있으면 제거
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)  # 파일도 삭제 (선택 사항)
                except Exception as e:
                    print(f"파일 삭제 실패: {e}")
        if self.current_index >= len(self.songs_list):
            self.current_index = -1
            self.current_song = ""
            self.player.stop()
            self.set_default_album_art()
            self.lbl_name.setText("재생할 곡을 선택하세요")
            self.lbl_Time.setText("00:00 / 00:00")
        self.save_playlist()  # 삭제 후 JSON 업데이트


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 30, 46))
    palette.setColor(QPalette.WindowText, QColor(226, 232, 240))
    app.setPalette(palette)
    player = MusicPlayer()
    player.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()