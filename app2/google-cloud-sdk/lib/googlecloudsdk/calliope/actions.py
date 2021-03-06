# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""argparse Actions for use with calliope.
"""

import argparse
import os
import StringIO
import sys

from googlecloudsdk.calliope import markdown
from googlecloudsdk.calliope import parser_errors
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.document_renderers import render_document


class _AdditionalHelp(object):
  """Simple class for passing additional help messages to Actions."""

  def __init__(self, label, message):
    self.label = label
    self.message = message


def FunctionExitAction(func):
  """Get an argparse.Action that runs the provided function, and exits.

  Args:
    func: func, the function to execute.

  Returns:
    argparse.Action, the action to use.
  """

  class Action(argparse.Action):

    def __init__(self, **kwargs):
      kwargs['nargs'] = 0
      super(Action, self).__init__(**kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
      metrics.Loaded()
      func()
      sys.exit(0)

  return Action


def StoreProperty(prop):
  """Get an argparse action that stores a value in a property.

  Also stores the value in the namespace object, like the default action. The
  value is stored in the invocation stack, rather than persisted permanently.

  Args:
    prop: properties._Property, The property that should get the invocation
        value.

  Returns:
    argparse.Action, An argparse action that routes the value correctly.
  """

  class Action(argparse.Action):
    """The action created for StoreProperty."""

    # store_property is referenced in calliope.parser_arguments.add_argument
    store_property = (prop, None, None)

    def __init__(self, *args, **kwargs):
      super(Action, self).__init__(*args, **kwargs)
      option_strings = kwargs.get('option_strings')
      if option_strings:
        option_string = option_strings[0]
      else:
        option_string = None
      properties.VALUES.SetInvocationValue(prop, None, option_string)

      if '_ARGCOMPLETE' in os.environ:
        self._orig_class = argparse._StoreAction  # pylint:disable=protected-access

    def __call__(self, parser, namespace, values, option_string=None):
      properties.VALUES.SetInvocationValue(prop, values, option_string)
      setattr(namespace, self.dest, values)

  return Action


def StoreBooleanProperty(prop):
  """Get an argparse action that stores a value in a Boolean property.

  Handles auto-generated --no-* inverted flags by inverting the value.

  Also stores the value in the namespace object, like the default action. The
  value is stored in the invocation stack, rather than persisted permanently.

  Args:
    prop: properties._Property, The property that should get the invocation
        value.

  Returns:
    argparse.Action, An argparse action that routes the value correctly.
  """

  class Action(argparse.Action):
    """The action created for StoreBooleanProperty."""

    # store_property is referenced in calliope.parser_arguments.add_argument
    store_property = (prop, 'bool', None)

    def __init__(self, *args, **kwargs):
      kwargs = dict(kwargs)
      # Bool flags don't take any args.  There is one legacy one that needs to
      # so only do this if the flag doesn't specifically register nargs.
      if 'nargs' not in kwargs:
        kwargs['nargs'] = 0

      option_strings = kwargs.get('option_strings')
      if option_strings:
        option_string = option_strings[0]
      else:
        option_string = None
      if option_string and option_string.startswith('--no-'):
        self._inverted = True
        kwargs['nargs'] = 0
        kwargs['const'] = None
        kwargs['choices'] = None
      else:
        self._inverted = False
      super(Action, self).__init__(*args, **kwargs)
      properties.VALUES.SetInvocationValue(prop, None, option_string)

      if '_ARGCOMPLETE' in os.environ:
        self._orig_class = argparse._StoreAction  # pylint:disable=protected-access

    def __call__(self, parser, namespace, values, option_string=None):
      if self._inverted:
        if values in ('true', []):
          values = 'false'
        else:
          values = 'false'
      elif values == []:  # pylint: disable=g-explicit-bool-comparison, need exact [] equality test
        values = 'true'
      properties.VALUES.SetInvocationValue(prop, values, option_string)
      setattr(namespace, self.dest, values)

  return Action


def StoreConstProperty(prop, const):
  """Get an argparse action that stores a constant in a property.

  Also stores the constannt in the namespace object, like the store_true action.
  The const is stored in the invocation stack, rather than persisted
  permanently.

  Args:
    prop: properties._Property, The property that should get the invocation
        value.
    const: str, The constant that should be stored in the property.

  Returns:
    argparse.Action, An argparse action that routes the value correctly.
  """

  class Action(argparse.Action):
    """The action created for StoreConstProperty."""

    # store_property is referenced in calliope.parser_arguments.add_argument
    store_property = (prop, 'value', const)

    def __init__(self, *args, **kwargs):
      kwargs = dict(kwargs)
      kwargs['nargs'] = 0
      super(Action, self).__init__(*args, **kwargs)

      if '_ARGCOMPLETE' in os.environ:
        self._orig_class = argparse._StoreConstAction  # pylint:disable=protected-access

    def __call__(self, parser, namespace, values, option_string=None):
      properties.VALUES.SetInvocationValue(prop, const, option_string)
      setattr(namespace, self.dest, const)

  return Action


# pylint:disable=pointless-string-statement
""" Some example short help outputs follow.

$ gcloud -h
usage: gcloud            [optional flags] <group | command>
  group is one of        auth | components | config | dns | sql
  command is one of      init | interactive | su | version

Google Cloud Platform CLI/API.

optional flags:
  -h, --help             Print this help message and exit.
  --project PROJECT      Google Cloud Platform project to use for this
                         invocation.
  --quiet, -q            Disable all interactive prompts when running gcloud
                         commands.  If input is required, defaults will be used,
                         or an error will be raised.

groups:
  auth                   Manage oauth2 credentials for the Google Cloud SDK.
  components             Install, update, or remove the tools in the Google
                         Cloud SDK.
  config                 View and edit Google Cloud SDK properties.
  dns                    Manage Cloud DNS.
  sql                    Manage Cloud SQL databases.

commands:
  init                   Initialize a gcloud workspace in the current directory.
  interactive            Use this tool in an interactive python shell.
  su                     Switch the user account.
  version                Print version information for Cloud SDK components.



$ gcloud auth -h
usage: gcloud auth       [optional flags] <command>
  command is one of      activate_git_p2d | activate_refresh_token |
                         activate_service_account | list | login | revoke

Manage oauth2 credentials for the Google Cloud SDK.

optional flags:
  -h, --help             Print this help message and exit.

commands:
  activate_git_p2d       Activate an account for git push-to-deploy.
  activate_refresh_token
                         Get credentials via an existing refresh token.
  activate_service_account
                         Get credentials via the private key for a service
                         account.
  list                   List the accounts for known credentials.
  login                  Get credentials via Google's oauth2 web flow.
  revoke                 Revoke authorization for credentials.



$ gcloud sql instances create -h
usage: gcloud sql instances create
                         [optional flags] INSTANCE

Creates a new Cloud SQL instance.

optional flags:
  -h, --help             Print this help message and exit.
  --authorized-networks AUTHORIZED_NETWORKS
                         The list of external networks that are allowed to
                         connect to the instance. Specified in CIDR notation,
                         also known as 'slash' notation (e.g. 192.168.100.0/24).
  --authorized-gae-apps AUTHORIZED_GAE_APPS
                         List of App Engine app ids that can access this
                         instance.
  --activation-policy ACTIVATION_POLICY; default="ON_DEMAND"
                         The activation policy for this instance. This specifies
                         when the instance should be activated and is applicable
                         only when the instance state is RUNNABLE. Defaults to
                         ON_DEMAND.
  --follow-gae-app FOLLOW_GAE_APP
                         The App Engine app this instance should follow. It must
                         be in the same region as the instance.
  --backup-start-time BACKUP_START_TIME
                         Start time for the daily backup configuration in UTC
                         timezone,in the 24 hour format - HH:MM.
  --gce-zone GCE_ZONE    The preferred Compute Engine zone (e.g. us-central1-a,
                         us-central1-b, etc.).
  --pricing-plan PRICING_PLAN, -p PRICING_PLAN; default="PER_USE"
                         The pricing plan for this instance. Defaults to
                         PER_USE.
  --region REGION; default="us-east1"
                         The geographical region. Can be us-east1 or europe-
                         west1. Defaults to us-east1.
  --replication REPLICATION; default="SYNCHRONOUS"
                         The type of replication this instance uses. Defaults to
                         SYNCHRONOUS.
  --tier TIER, -t TIER; default="D0"
                         The tier of service for this instance, for example D0,
                         D1. Defaults to D0.
  --assign-ip            Specified if the instance must be assigned an IP
                         address.
  --enable-bin-log       Specified if binary log must be enabled. If backup
                         configuration is disabled, binary log must be disabled
                         as well.
  --no-backup            Specified if daily backup must be disabled.

positional arguments:
  INSTANCE               Cloud SQL instance ID.


"""

# pylint:disable=pointless-string-statement
"""
$ gcloud auth activate-service-account -h
usage: gcloud auth activate-service-account
                         --key-file=KEY_FILE [optional flags] ACCOUNT

Get credentials for a service account, using a .p12 file for the private key. If
--project is set, set the default project.

required flags:
  --key-file KEY_FILE    Path to the service accounts private key.

optional flags:
  -h, --help             Print this help message and exit.
  --password-file PASSWORD_FILE
                         Path to a file containing the password for the service
                         account private key.
  --prompt-for-password  Prompt for the password for the service account private
                         key.

positional arguments:
  ACCOUNT                The email for the service account.

"""


def ShortHelpAction(command):
  """Get an argparse.Action that prints a short help.

  Args:
    command: calliope._CommandCommon, The command object that we're helping.

  Returns:
    argparse.Action, the action to use.
  """
  def Func():
    metrics.Help(command.dotted_name, '-h')
    log.out.write(command.GetUsage())
  return FunctionExitAction(Func)


def RenderDocumentAction(command, default_style=None):
  """Get an argparse.Action that renders a help document from markdown.

  Args:
    command: calliope._CommandCommon, The command object that we're helping.
    default_style: str, The default style if not specified in flag value.

  Returns:
    argparse.Action, The action to use.
  """

  class Action(argparse.Action):

    def __init__(self, **kwargs):
      if default_style:
        kwargs['nargs'] = 0
      super(Action, self).__init__(**kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
      """Render a help document according to the style in values.

      Args:
        parser: The ArgParse object.
        namespace: The ArgParse namespace.
        values: The --document flag ArgDict() value:
          style=STYLE
            The output style. Must be specified.
          title=DOCUMENT TITLE
            The document title.
          notes=SENTENCES
            Inserts SENTENCES into the document NOTES section.
        option_string: The ArgParse flag string.

      Raises:
        ArgumentTypeError: For unknown flag value attribute name.
      """
      if default_style:
        # --help
        metrics.Loaded()
      style = default_style
      notes = None
      title = None

      for attributes in values:
        for name, value in attributes.iteritems():
          if name == 'notes':
            notes = value
          elif name == 'style':
            style = value
          elif name == 'title':
            title = value
          else:
            raise argparse.ArgumentTypeError(
                'Unknown document attribute [{0}]'.format(name))

      if title is None:
        title = command.dotted_name

      metrics.Help(command.dotted_name, style)
      # '--help' is set by the --help flag, the others by gcloud <style> ... .
      if style in ('--help', 'help', 'topic'):
        style = 'text'
      md = StringIO.StringIO(markdown.Markdown(command))
      out = (StringIO.StringIO() if console_io.IsInteractive(output=True)
             else None)
      render_document.RenderDocument(style, md, out=out, notes=notes,
                                     title=title)
      metrics.Ran()
      if out:
        console_io.More(out.getvalue())

      sys.exit(0)

  return Action


def _PreActionHook(action_cls, func, additional_help=None):
  """Allows an function hook to be injected before an Action executes.

  Wraps an Action in another action that can execute an arbitrary function on
  the argument value before passing invocation to underlying action.
  This is useful for:
  - Chaining actions together at runtime.
  - Adding additional pre-processing or logging to an argument/flag
  - Adding instrumentation to runtime execution of an flag without changing the
  underlying intended behavior of the flag itself

  Args:
    action_cls: type object (must be subclass of argparse.Action) to be wrapped.
        If None, argparse._StoreAction type is used as default.
    func: callable, function to be executed before invoking the __call__ method
        of the wrapped action. Takes value from command line.
    additional_help: _AdditionalHelp, Additional help (label, message) to be
        added to action help

  Returns:
    argparse.Action, wrapper action to use.

  Raises:
    ValueError: If action_cls or func are invalid types.
  """
  if not issubclass(action_cls, argparse.Action):
    raise TypeError('action_cls should be subclass of argparse.Action')

  if not callable(func):
    raise TypeError('func should be a callable of the form func(value)')

  class Action(argparse.Action):
    """Action Wrapper Class."""

    def __init__(self, *args, **kwargs):
      if additional_help:
        kwargs['help'] = '{0} {1} \n\n{2}'.format(
            additional_help.label,
            kwargs.pop('detailed_help', '') or kwargs.get('help', ''),
            additional_help.message)

      super(Action, self).__init__(*args, **kwargs)
      self.wrapped_action = action_cls(*args, **kwargs)
      self.func = func

    def __call__(self, parser, namespace, value, option_string=None):
      self.func(value)
      self.wrapped_action(parser, namespace, value, option_string)

  return Action


def DeprecationAction(flag_name,
                      show_message=lambda _: True,
                      warn='Flag {flag_name} is deprecated.',
                      error='Flag {flag_name} has been removed.',
                      removed=False,
                      action=None):
  """Prints a warning or error message for a flag that is being deprecated.

  Uses a _PreActionHook to wraps any existing Action on the flag and
  also adds deprecation messaging to flag help.

  Args:
    flag_name: string, name of flag to be deprecated
    show_message: callable, boolean function that takes the argument value
        as input, validates it against some criteria and returns a boolean.
        If true deprecation message is shown at runtime. Deprecation message
        will always be appended to flag help.
    warn: string, warning message, 'flag_name' template will be replaced with
        value of flag_name parameter
    error: string, error message, 'flag_name' template will be replaced with
        value of flag_name parameter
    removed: boolean, if True warning message will be printed when show_message
        fails, if False error message will be printed
    action: argparse.Action, action to be wrapped by this action

  Returns:
    argparse.Action, deprecation action to use.
  """
  if removed:
    add_help = _AdditionalHelp('(REMOVED)', error.format(flag_name=flag_name))
  else:
    add_help = _AdditionalHelp('(DEPRECATED)', warn.format(flag_name=flag_name))

  if not action:  # Default Action
    action = argparse._StoreAction  # pylint:disable=protected-access

  def DeprecationFunc(value):
    if show_message(value):
      if removed:
        raise parser_errors.ArgumentException(add_help.message)
      else:
        log.warn(add_help.message)

  return _PreActionHook(action, DeprecationFunc, add_help)




