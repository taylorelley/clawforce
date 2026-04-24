"""Chat channels module with plugin architecture."""

from specops_lib.channels.base import BaseChannel
from specops_lib.channels.manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
