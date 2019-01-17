#!/usr/bin/python
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible.errors import AnsibleError
from ansible.module_utils import common_koji


ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}


DOCUMENTATION = '''
---
module: koji_cg

short_description: Create and manage Koji content generators
description:
   - This module can grant or revoke access to a `content generator
     <https://docs.pagure.org/koji/content_generators/>`_ for a user account.
   - Note, this method tries to call the "grantCGAccess" RPC on every run
     because we have no ability to query the current state. See the `listCGs
     <https://pagure.io/koji/pull-request/1160>`_ hub RPC in progress.

options:
   name:
     description:
       - The name of the Koji content generator. Example: "debian".
     required: true
   user:
     description:
       - The name of the Koji user account. Example: "cguser".
       - This user account must already exist in Koji's database. For example,
         you may run an authenticated "koji hello" command to create the
         account database entry.
     required: true
requirements:
  - "python >= 2.7"
  - "koji"
'''

EXAMPLES = '''
- name: Grant a user access to a content generator.
  hosts: localhost
  tasks:
    - name: Grant access to the rcm/debbuild account
      koji_cg:
        name: debian
        user: rcm/debbuild
        state: present
'''

RETURN = ''' # '''


def run_module():
    module_args = dict(
        koji=dict(type='str', required=False),
        name=dict(type='str', required=True),
        user=dict(type='str', required=True),
        state=dict(type='str', required=False, default='present'),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        # check mode needs https://pagure.io/koji/pull-request/1160
        supports_check_mode=False
    )

    if not common_koji.HAS_KOJI:
        module.fail_json(msg='koji is required for this module')

    params = module.params
    profile = params['koji']
    name = params['name']
    user = params['user']
    state = params['state']

    session = common_koji.get_session(profile)

    result = {'changed': False}

    # There are no "get" methods for content generator information, so we must
    # send the changes to Koji every time.
    # in-progress "listCGs" pull request:
    # https://pagure.io/koji/pull-request/1160

    common_koji.ensure_logged_in(session)

    if state == 'present':
        # The "grant" method will at least raise an error if the permission was
        # already granted, so we can set the "changed" result based on that.
        try:
            session.grantCGAccess(user, name, create=True)
            result['changed'] = True
        except common_koji.koji.GenericError as e:
            if 'User already has access to content generator' not in str(e):
                raise AnsibleError(to_native(e))
    elif state == 'absent':
        # There's no indication whether this changed anything, so we're going
        # to be pessimistic and say we're always changing it.
        session.revokeCGAccess(user, name)
        result['changed'] = True
    else:
        module.fail_json(msg="State must be 'present' or 'absent'.",
                         changed=False, rc=1)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
