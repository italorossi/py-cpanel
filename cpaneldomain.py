#!/usr/bin/env python2.4
# -*- coding: utf-8 -*-

import sys
import os
import re
import time

from util import *

##########################################################################    
# 
#   CpanelDomain Class
#
##########################################################################
class CpanelDomain(object):
    def __new__(cls, domain_name):
        if is_hosted(domain_name):
            return object.__new__(cls, domain_name)
        else:
            raise ValueError("Domain not found!")
        
    def __init__(self, domain_name):
        self.domain_name = domain_name
        self.admin_user = self._get_admin_user()
        self.used_space = self._get_used_space()
        self.email_accounts = self._get_email_accounts()
        self.used_bandwidth = self._get_used_bandwidth()
        self.redirects = self._get_redirects()
    @property
    def __dict__(self):
        """Return dict with all informations available about this domain"""
        return dict(admin_user=self.admin_user, domain_name=self.domain_name, \
                    used_space=self.used_space, email_accounts=self.email_accounts, \
                    used_bandwidth=self.used_bandwidth, redirects=self.redirects, \
                    quota_limit=self.quota_limit, contactemail=self.contactemail, \
                    hosting_plan=self.hosting_plan, suspended=self.suspended)
    
    def _get_admin_user(self):
        """Return the admin user"""
        domains = get_domains()
        return domains[self.domain_name]
    
    def _get_used_space(self):
        """Return the total space used in bytes"""
        repquota = get_repquota()
        return repquota[self.admin_user]["used_space"]
    
    def _get_quota_limit(self):
        """Return the quota limit in bytes"""
        repquota = get_repquota()
        return repquota[self.admin_user]["quota_limit"]
    
    def _set_quota_limit(self, new_quota):
        """Set a new quota for a domain"""
        if type(new_quota) != int:
            raise ValueError("Please provide an integer in MegaBytes!")
        
        # Cpanel script syntax!
        new_quota = str(new_quota) + "M"
        cmd = ["/scripts/editquota", self.admin_user, new_quota]
        result, out, err = execute_command(cmd)
        if result != 0:
            raise ValueError("Error setting new quota: %s" % err)
        update_cpanel_cache()
        return new_quota
    
    quota_limit = property(_get_quota_limit, _set_quota_limit)
    
    def _get_contactemail(self):
        """Return de contactemail"""
        contactemail = open(contactemail_file % self.admin_user).read()
        return contactemail.strip()
    
    def _set_contactemail(self, new_contactemail):
        """Set new contacemail for domain"""
        # Updating .contacemail file
        new_contactemail = str(new_contactemail)
        contactemail = open(contactemail_file % self.admin_user, "w")
        contactemail.write(new_contactemail)
        contactemail.close()
        # Updating hosting plan
        plan = self.hosting_plan
        plan["CONTACTEMAIL"] = new_contactemail
        self.hosting_plan = plan
        update_cpanel_cache()
        return new_contactemail
    
    contactemail = property(_get_contactemail, _set_contactemail)
    
    def _get_email_accounts(self):
        """Return all email accounts with their quota limits and used space"""
        dict_mailaccounts = get_mailaccounts(self.admin_user, self.domain_name)
        if len(dict_mailaccounts) == 0:
            return dict_mailaccounts
        
        dict_mailaccounts_quotas = get_mailaccounts_quota_limit(self.admin_user, \
                                                                    self.domain_name)
        for mailaccount in dict_mailaccounts:
            try:
                dict_mailaccounts[mailaccount]["quota_limit"] = dict_mailaccounts_quotas[mailaccount]
            except KeyError:
                # Email accounts with unlimited quota.
                dict_mailaccounts[mailaccount]["quota_limit"] = None
            
            dict_mailaccounts[mailaccount]["used_space"] = get_mailaccounts_used_space(self.admin_user, \
                                                            self.domain_name, mailaccount)
        return dict_mailaccounts
    
    def _get_used_bandwidth(self):
        """Read /var/cpanel/bandwidth/domainname and get the bandwidth used"""
        this_month = time.localtime()[1] 
        this_year = time.localtime()[0]
        try:
            lines = open(bandwidth_file % self.domain_name).readlines()
        except Exception, e:
            return 0
        
        bandwidth_sizes = []
        for line in lines:
            if re.match(r'%s\.\d{1,2}\.%s-all=\d{1,}$' % (this_month, this_year), line):
                bandwidth_sizes.append(line.split("=")[-1])
        count = 0
        for size in bandwidth_sizes:
            count = count + int(size.strip())
        return count
    
    def _get_hosting_plan(self):
        """Return the hosting plan"""
        hosting_plan = open(plan_file % self.admin_user).readlines()
        conf = {}
        for line in hosting_plan:
            if not line.startswith("#"):  # Comments
                key, value = line.strip().split("=")
                conf[key] = value.isdigit() and int(value) or value
        return conf

    def _set_hosting_plan(self, new_hosting_plan):
        """Receive new_hosting_plan as dict and rewrite it!"""
        if type(new_hosting_plan) != dict:
            raise ValueError("Please provide a dict with the new hosting plan!")
            
        hosting_plan = open(plan_file % self.admin_user, "w")
        for key in new_hosting_plan:
            line = "%s=%s\n" % (key, new_hosting_plan[key])
            hosting_plan.write(line)
        hosting_plan.close()
        update_cpanel_cache()
        return new_hosting_plan
    
    hosting_plan = property(_get_hosting_plan, _set_hosting_plan)

    def _get_suspended(self):
        """True for suspended and False for active domain"""
        return os.path.exists(suspended_file % self.admin_user)
    
    def _set_suspended(self, value):
        """True for suspend the domain and False to activate"""
        cmd = value and "suspendacct" or "unsuspendacct"
        cmd = "/scripts/" + cmd
        result, out, err = execute_command([cmd, self.admin_user])
        if result != 0:
            raise ValueError("Error (Un)suspedind domain: %s" % err)
        update_cpanel_cache()
        return value
    
    suspended = property(_get_suspended, _set_suspended)

    def _get_redirects(self):
        """Return the redicts"""
        if not os.path.exists(redirects_file % self.domain_name):
            return []
        
        redirects = open(redirects_file % self.domain_name).readlines()
        redirects_source_dest = []
        for redirect in redirects:
            # Making catch all visible
            redirect = redirect.replace(":fail:No Such User Here", "none").replace("*", "catchall")
            source, destination = redirect.strip().split(":")[:2]
            redirects_source_dest.append(dict(source=source, destination=destination))
        return redirects_source_dest
    

