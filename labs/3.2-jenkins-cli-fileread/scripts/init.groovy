import jenkins.model.Jenkins
import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import jenkins.install.InstallState
def j = Jenkins.get()
if (!(j.securityRealm instanceof HudsonPrivateSecurityRealm)) {
  def realm = new HudsonPrivateSecurityRealm(false)
  realm.createAccount('labadmin', System.getenv('LAB_ADMIN_PASSWORD'))
  j.setSecurityRealm(realm)
}
def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
j.setAuthorizationStrategy(strategy)
j.setInstallState(InstallState.INITIAL_SETUP_COMPLETED)
j.save()
new File(j.rootDir, 'lab-marker.txt').text = 'CICD-LAB32-HARMLESS-MARKER\nSECOND-LINE-DEMO\n'
