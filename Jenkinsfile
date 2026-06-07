pipeline {
  agent any

  options {
    disableConcurrentBuilds()
    timestamps()
  }

  environment {
    DEPLOY_HOST = credentials('prod-deploy-host')
    DEPLOY_USER = credentials('prod-deploy-user')
    DEPLOY_PATH = '/opt/assistente-pessoal'
    APP_SERVICE_NAME = 'assistente-pessoal'
  }

  triggers {
    pollSCM('H/2 * * * *')
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Validate Branch') {
      steps {
        script {
          def branch = env.BRANCH_NAME ?: sh(script: 'git rev-parse --abbrev-ref HEAD', returnStdout: true).trim()
          if (branch != 'prod') {
            currentBuild.result = 'NOT_BUILT'
            error("Build ignorado: branch '${branch}'. Apenas 'prod' faz deploy.")
          }
        }
      }
    }

    stage('Deploy') {
      steps {
        sshagent(credentials: ['prod-ssh-key']) {
          sh '''
            ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST} \
              "cd ${DEPLOY_PATH} && APP_SERVICE_NAME=${APP_SERVICE_NAME} bash scripts/deploy_prod.sh"
          '''
        }
      }
    }
  }

  post {
    success {
      echo 'Deploy finalizado com sucesso.'
    }
    failure {
      echo 'Falha no pipeline de deploy.'
    }
  }
}
