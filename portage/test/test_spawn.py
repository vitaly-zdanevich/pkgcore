# Copyright: 2005 Brian Harring <ferringb@gmail.com>
# License: GPL2

from twisted.trial import unittest
from portage import spawn
from portage.test.fs.test_util import TempDirMixin
from portage.util.currying import post_curry
import os, pwd, signal

class SpawnTest(TempDirMixin, unittest.TestCase):
	
	def __init__(self, *a, **kw):
		try:
			self.bash_path = spawn.find_binary("bash")
			self.null_file = open("/dev/null", "w")
			self.null = self.null_file.fileno()
		except spawn.CommandNotFound:
			self.skip = "bash wasn't found.  this will be ugly."
		super(SpawnTest, self).__init__(*a, **kw)
		
	def setUp(self):
		self.orig_env = os.environ["PATH"]
		TempDirMixin.setUp(self)
		os.environ["PATH"] = ":".join([self.dir] + self.orig_env.split(":"))

	def tearDown(self):
		os.environ["PATH"] = self.orig_env
		TempDirMixin.tearDown(self)
		
	def test_find_binary(self):
		script_name = "portage-findpath-test.sh"
		self.assertRaises(spawn.CommandNotFound, spawn.find_binary, script_name)
		fp = os.path.join(self.dir, script_name)
		open(fp,"w")
		os.chmod(fp, 0650)
		self.assertRaises(spawn.CommandNotFound, spawn.find_binary, script_name)
		os.chmod(fp, 0750)
		self.failUnlessSubstring(self.dir, spawn.find_binary(script_name))
		os.unlink(fp)
	
	def generate_script(self, filename, text):
		if not os.path.isabs(filename):
			fp = os.path.join(self.dir, filename)
		open(fp, "w").write(text)
		os.chmod(fp, 0750)
		return fp
	
	def test_get_output(self):
		filename = "portage-spawn-getoutput.sh"
		for r, s, text, args in [
			[0, ["dar\n"], "echo dar\n", {}],
			[0, ["dar"], "echo -n dar", {}],
			[1, ["blah\n","dar\n"], "echo blah\necho dar\nexit 1", {}],
			[0, [], "echo dar 1>&2", {"fd_pipes":{1:1,2:self.null}}]]:

			fp = self.generate_script(filename, text)
			self.assertEqual([r,s], spawn.spawn_get_output(fp, spawn_type=spawn.spawn_bash, **args))

		os.unlink(fp)

	# should probably use a mixin for these.
	def test_sandbox(self):
		try:
			spawn.find_binary("sandbox")
		except spawn.CommandNotFound:
			raise unittest.SkipTest("sandbox is not available, thus testing isn't possible")
		self.assertTrue(spawn.sandbox_capable, "sandbox_capable boolean test")
		fp = self.generate_script("portage-spawn-sandbox.sh", "echo $LD_PRELOAD")
		self.failUnlessSubstring("/libsandbox.so", spawn.spawn_get_output(fp, spawn_type=spawn.spawn_sandbox)[1][0])
		os.unlink(fp)

	def test_fakeroot(self):
		try:
			spawn.find_binary("fakeroot")
		except spawn.CommandNotFound:
			raise unittest.SkipTest("fakeroot is not available, thus testing isn't possible")
		self.assertTrue(spawn.fakeroot_capable, "fakeroot_capable boolean test")
		fp = os.path.join(self.dir, "portage-spawn-fakeroot.sh")
		
		try:
			l = pwd.getpwnam("nobody")
		except KeyError:
			raise unittest.SkipTest("system lacks nobody user, thus can't test fakeroot")

		nobody_uid = l[2]
		nobody_gid = l[3]

		kw = {}
		if os.getuid() == 0:
			kw = {"uid":l[2], "gid":l[3]}

		fp2 = self.generate_script("portage-spawn-fakeroot2.sh",
			"#!%s\nimport os\ns=os.stat('/tmp')\nprint s.st_uid\nprint s.st_gid\n" % 
			spawn.find_binary("python"))
		
		fp1 = self.generate_script("portage-spawn-fakeroot.sh", 
			"#!%s\nchown %i:%i /tmp;%s;\n" % (self.bash_path, nobody_uid, nobody_gid, fp2))

		savefile = os.path.join(self.dir, "fakeroot-savefile")
		self.assertNotEqual(long(os.stat("/tmp").st_uid), long(nobody_uid))
		self.assertEqual([0, ["%s\n" % x for x in (nobody_uid, nobody_gid)]],
			spawn.spawn_get_output([self.bash_path, fp1], 
			spawn_type=post_curry(spawn.spawn_fakeroot, savefile), **kw))
		self.assertNotEqual(long(os.stat("/tmp").st_uid), long(nobody_uid), 
			"bad voodoo; we managed to change /tmp to nobody- this shouldn't occur!")
		self.assertEqual(True, os.path.exists(savefile), 
			"no fakeroot file was created, either fakeroot differs or our" +
			" args passed to it are bad")

		# yes this is a bit ugly, but fakeroot requires an arg- so we have to curry it
		self.assertEqual([0, ["%s\n" % x for x in (nobody_uid, nobody_gid)]],
			spawn.spawn_get_output([fp2], 
			spawn_type=post_curry(spawn.spawn_fakeroot, savefile), **kw))

		os.unlink(fp1)
		os.unlink(fp2)
		os.unlink(savefile)

	def test_process_exit_code(self):
		self.assertEqual(0, spawn.process_exit_code(0), "exit code failed")
		self.assertEqual(16, spawn.process_exit_code(16 << 8), "signal exit code failed")

	def generate_background_pid(self):
		try:
			return spawn.spawn(["sleep", "3600s"], returnpid=True)[0]
		except CommandNotFound:
			raise unittest.SkipTest("can't complete the test, sleep binary doesn't exist")

	def test_spawn_returnpid(self):
		pid = self.generate_background_pid()
		try:
			self.assertEqual(None, os.kill(pid, 0), "returned pid was invalid, or sleep died")
			self.assertEqual(True, pid in spawn.spawned_pids, "pid wasn't recorded in global pids")
		finally:
			os.kill(pid, signal.SIGKILL)

	def test_cleanup_pids(self):
		pid = self.generate_background_pid()
		spawn.cleanup_pids([pid])
		self.assertRaises(OSError, post_curry(os.kill, pid, 0))
		self.failIfIn(pid, spawn.spawned_pids, "pid wasn't removed from global pids")

	def test_bash(self):
		# bash builtin for true without exec'ing true (eg, no path lookup)
		self.assertEqual(0, spawn.spawn_bash(":"))

	def test_logfile(self):
		log_fp = os.path.join(self.dir, "logfile_test")
		out_file = os.path.join(self.dir, "logfile_result")
		text = "grande tiza"
		fp = self.generate_script("logfile.sh", "#!%s\necho %s\n" % (self.bash_path, text))
		self.assertEqual(0, spawn.spawn(fp, logfile=log_fp, fd_pipes={1:self.null, 2:1}))
		self.assertEqual(text, open(log_fp).read().rstrip("\n"), "logged text differed")

	def test_umask(self):
		fp = self.generate_script("portage_spawn_umask.sh", "#!%s\numask" % self.bash_path)
		try:
			old_um = os.umask(0)
			if old_um == 0:
				# crap.
				desired = 022
				os.umask(desired)
			else:
				desired = 0
			self.assertEqual(str(desired).lstrip("0"), 
				spawn.spawn_get_output(fp)[1][0].strip().lstrip("0"))
		finally:
			os.umask(old_um)

