from dataclasses import dataclass


@dataclass
class NowPlaying:
    artist: str
    album: str
    title: str

    def display(self, lines: int) -> str:
        if lines == 1:
            return self.title
        elif lines == 2:
            return f"{self.artist}\n{self.title}"
        else:
            return f"{self.artist}\n{self.album}\n{self.title}"
