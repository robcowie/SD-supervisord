#!/usr/bin/env python

"""
Server Density Supervisord plugin.
Track the number of processes in each state.

For possible states see the docs at 
http://supervisord.org/subprocess.html#process-states
"""

import httplib
import urllib
import xmlrpclib


SUPERVISORD_RPC_URL = "http://localhost:9001/RPC2"
DEFAULT_STATE_COUNTS = dict(STOPPED=0, STARTING=0, RUNNING=0, BACKOFF=0, 
                            STOPPING=0, EXITED=0, FATAL=0, UNKNOWN=0)


class _Counter(dict):
    """See http://code.activestate.com/recipes/576611/"""
    def __init__(self, iterable=None, **kargs):
        self.update(iterable, **kargs)
    
    def update(self, iterable=None, **kargs):
        if iterable is not None:
            if hasattr(iterable, 'iteritems'):
                if self:
                    self_get = self.get
                    for elem, count in iterable.iteritems():
                        self[elem] = self_get(elem, 0) + count
                else:
                    dict.update(self, iterable) # fast path when counter is empty
            else:
                self_get = self.get
                for elem in iterable:
                    self[elem] = self_get(elem, 0) + 1
        if kargs:
            self.update(kargs)

try:
    from collections import Counter
except ImportError:
    Counter = _Counter


class Supervisord(object):
    """Collect and return details of a local Supervisord instance.
    """
    def __init__(self, agent_config, checks_logger, raw_config):
        self.agent_config = agent_config
        self.checks_logger = checks_logger
        self.raw_config = raw_config
    
    def run(self):
        stats = {}
        
        try:
            # # Pull the supervisord rpc URL from the config or default
            url = self.raw_config['Main'].get('supervisord_rpc_url',
                    SUPERVISORD_RPC_URL)
            server = xmlrpclib.Server(url)
        except KeyError:
            # Should only happen if Main section of config is missing
            self.checks_logger.error('Missing sd-agent configuration')
            server = xmlrpclib.Server(SUPERVISORD_RPC_URL)
            
        try:
            server_info = server.supervisor.getAllProcessInfo()
            self.checks_logger.debug(server_info)
            stats.update(self.get_process_counts(server_info))
        except (xmlrpclib.Fault, httplib.HTTPException), exc:
            stats = {}
            self.checks_logger.debug(str(exc))
        return stats
    
    def get_process_counts(self, server_info):
        counter = Counter(DEFAULT_STATE_COUNTS)
        counter.update([process['statename'] for process in server_info])
        return counter
