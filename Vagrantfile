Vagrant.configure('2') do |config|
  config.vm.box = 'bento/ubuntu-24.04'
  config.vm.boot_timeout = 600
  config.vm.synced_folder '.', '/vagrant', disabled: true

  config.vm.define 'Master' do |master|
    master.vm.hostname = 'k3s-master'
    master.vm.network 'private_network',
      ip: '192.168.58.10',
      virtualbox__intnet: 'orchestrator-network'
    master.vm.network 'forwarded_port',
      guest: 6443,
      host: 16443,
      host_ip: '127.0.0.1',
      id: 'k3s_api'

    master.vm.provider 'virtualbox' do |virtualbox|
      virtualbox.name = 'orchestrator-master'
      virtualbox.memory = 3072
      virtualbox.cpus = 2
    end
  end

  config.vm.define 'Agent' do |agent|
    agent.vm.hostname = 'k3s-agent'
    agent.vm.network 'private_network',
      ip: '192.168.58.11',
      virtualbox__intnet: 'orchestrator-network'

    agent.vm.provider 'virtualbox' do |virtualbox|
      virtualbox.name = 'orchestrator-agent'
      virtualbox.memory = 2048
      virtualbox.cpus = 1
    end
  end
end
