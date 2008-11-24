import os
from subprocess import Popen, PIPE, call

# Home directories for domains
domains_home_path = "/home"

# The file that constains the contacemail of a domain
# /home/adminuser/.contacemail
contactemail_file = "/home/%s/.contactemail"

# All the email accounts from a domain
# /home/adminusers/etc/domainname/passwd
mailaccounts_file = "/home/%s/etc/%s/passwd"

# Quota limits for all the email accounts from a domain
# /home/adminuser/etc/domainname/quota
mailaccounts_quotas_file = "/home/%s/etc/%s/quota"

# Mail redirects for a domain
# /etc/valiases/domainname
redirects_file = "/etc/valiases/%s"

# The suspended domains are stored here
# /var/cpanel/suspended/adminuser
suspended_file = "/var/cpanel/suspended/%s"

# Hosting Plan for domains that contains all the features availables
# /var/cpanel/users/adminuser
plan_file = "/var/cpanel/users/%s"

# List with all domains followed by respective adminusers
# domainname: adminuser
domains_admin_users_file = "/etc/trueuserdomains"

# Bandwidth account file
# /var/cpanel/bandwidth/domainname
bandwidth_file = "/var/cpanel/bandwidth/%s"

# General Functions
def unsuspend_bwlimited(domain):
    """Unsuspend bwlimited domain""" 
    call(["rm", "-f", "/var/cpanel/bwlimited/%s" % domain.admin_user])
    call(["rm", "-f", "/var/cpanel/bwlimited/%s" % domain.domain_name])
    call(["rm", "-f", "/var/cpanel/bwlimited/www.%s" % domain.domain_name])

def update_cpanel_cache():
    """Run /scripts/updateuserdomains to update cpanel cache"""
    call(["/scripts/updateuserdomains"])
    # Removing another cache files
    call(["rm", "-rf", "/var/cpanel/users.cache/"])

def get_domains():
    """Dict with all domains and admin users hosted"""
    file_lines = open(domains_admin_users_file).readlines()
    domains = {}
    for line in file_lines:
        domain, admin_user = line.strip().replace(" ","").split(":")
        domains[domain] = admin_user
    return domains

def is_hosted(domain_name):
    """Check if domain_name is hosted on this server"""
    domains = get_domains()
    return domains.has_key(domain_name)

def execute_command(args):
    """ 
    result, out, err = exec(args)
    if result != 0:
        # error executing command!!
    """
    cmd = Popen(args, stderr=PIPE, stdout=PIPE)
    out = cmd.stdout.readlines()
    err = cmd.stderr.readlines()
    cmd.stdout.close()
    cmd.stderr.close()
    result = cmd.wait()
    return result, out, err

def parse_to_bytes(size):
    """
    MegaBytes/GigaBytes To Bytes.
    """
    if "M" in size:
        size = size.split("M")[0]
        size = int(size) * 1024 * 1024
    elif "G" in size:
        size = size.split("G")[0]
        size = int(size) * 1024 * 1024 * 1024
    return int(size)

def get_repquota():
    result, out, err = execute_command(["/usr/sbin/repquota", "-u", "/home", "-s"])
    if result != 0:
        raise ValueError("Can't execute /usr/sbin/repquota")
    
    lines = [line.split() for line in out[5:-2]]
    # Getting only username, used space and quota limit
    repquota = {}
    for line in lines:
        username = line[0]
        used_space = line[2]
        quota_limit = line[3]
        repquota[username] = {}
        repquota[username]["used_space"] = parse_to_bytes(used_space)
        repquota[username]["quota_limit"] = parse_to_bytes(quota_limit)
    return repquota

def get_mailaccounts(adminuser, domain_name):
    """Return dict with all email accounts"""
    try:
        lines_mailaccounts = open(mailaccounts_file % \
                             (adminuser, domain_name)).readlines()
    except Exception, e:
        return {}
    
    dict_mailaccounts = {}
    for line in lines_mailaccounts:
        username = line.split(":")[0]
        dict_mailaccounts[username] = {}
    return dict_mailaccounts

def get_mailaccounts_quota_limit(adminuser, domain_name):
    """Return dict with quota limit for each email account"""
    lines_mailaccounts_quotas = open(mailaccounts_quotas_file \
                                     % (adminuser, domain_name)).readlines()
    dict_mailaccounts_quotas = {}
    for line in lines_mailaccounts_quotas:
        username = line.split(":")[0]
        quota_limit = line.split(":")[1].strip()
        dict_mailaccounts_quotas[username] = int(quota_limit)
    return dict_mailaccounts_quotas

def get_mailaccounts_used_space(adminuser, domain_name, mail_account):
    """Return with used space for mail_account"""
    mailaccounts_home_path = domains_home_path + "/" + adminuser + \
                             "/mail/" + domain_name + "/" + mail_account
    result, out, err = execute_command(["/usr/bin/du", "-b", "-s", mailaccounts_home_path])
    if result != 0:
        raise ValueError("Can't get used space for account: %s" % err)
    line = out[0].strip()
    used_space = line.split("\t")[0]
    return int(used_space)
