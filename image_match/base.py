from abc import ABC, abstractmethod


class ImageMatcher(ABC):
    @abstractmethod
    def match(self, background, target):
        """
        返回:

        {
            x:
            y:
            score:
        }
        """
        pass
